"""Durable assessment jobs. The database row survives a worker restart."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commercial.models import AssessmentJob
from app.config import Settings
from app.engine.runner import execute_assessment
from app.errors import AppError
from app.models.assessments import Assessment
from app.models.base import utcnow
from app.security_log import security_event


def enqueue_job(db: Session, settings: Settings, assessment: Assessment, user_id: str | None) -> Assessment:
    existing = db.scalar(
        select(AssessmentJob).where(
            AssessmentJob.assessment_id == assessment.id,
            AssessmentJob.status.in_(("queued", "running")),
        )
    )
    if existing is not None:
        return assessment
    org_running = db.scalar(
        select(func.count()).select_from(AssessmentJob).where(
            AssessmentJob.organisation_id == assessment.organisation_id,
            AssessmentJob.status.in_(("queued", "running")),
        )
    ) or 0
    if org_running >= settings.max_concurrent_assessments_per_org:
        security_event("execution_limited", organisation_id=assessment.organisation_id, actor_user_id=user_id, outcome="denied", scope="organisation")
        raise AppError(429, "execution_limited", "This organisation already has the maximum number of assessments running.")
    global_running = db.scalar(
        select(func.count()).select_from(AssessmentJob).where(AssessmentJob.status.in_(("queued", "running")))
    ) or 0
    if global_running >= settings.max_concurrent_assessments_global:
        security_event("execution_limited", organisation_id=assessment.organisation_id, actor_user_id=user_id, outcome="denied", scope="global")
        raise AppError(429, "execution_limited", "The platform is at its execution capacity. Try again shortly.")
    job = AssessmentJob(
        organisation_id=assessment.organisation_id,
        assessment_id=assessment.id,
        triggered_by_user_id=user_id,
        status="queued",
        attempts=0,
        error_summary="",
    )
    db.add(job)
    db.commit()
    if settings.environment == "test" or not settings.celery_broker_url:
        run_job(db, settings, job.id)
        db.refresh(assessment)
        return assessment
    from app.commercial.tasks import run_assessment_task

    run_assessment_task.delay(job.id)
    assessment.status = "queued"
    db.commit()
    db.refresh(assessment)
    return assessment


def run_job(db: Session, settings: Settings, job_id: str) -> None:
    job = db.get(AssessmentJob, job_id)
    if job is None or job.status in {"succeeded", "cancelled"}:
        return
    if job.attempts >= 3 and job.status == "failed":
        return
    job.status = "running"
    job.attempts += 1
    job.started_at = utcnow()
    db.commit()
    try:
        execute_assessment(db, settings, job.assessment_id)
        assessment = db.get(Assessment, job.assessment_id)
        if assessment and assessment.status == "cancelled":
            job.status = "cancelled"
        else:
            job.status = "succeeded"
        job.finished_at = utcnow()
        db.commit()
    except Exception:
        job.status = "failed"
        job.error_summary = "The worker could not finish this assessment."
        job.finished_at = utcnow()
        assessment = db.get(Assessment, job.assessment_id)
        if assessment and assessment.status == "running":
            assessment.status = "failed"
            assessment.error_summary = job.error_summary
        db.commit()
