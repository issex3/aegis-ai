"""Baselines, regression, schedules, and finding workflow."""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.engine.operations import plan_assessment, start_assessment
from app.errors import AppError
from app.intelligence.pipeline import contribute_assessment
from app.intelligence.regression import compare_results
from app.intelligence.scoring import WEIGHTS, score_assessment
from app.models.agents import Agent, AgentIntegration
from app.models.assessments import Assessment, AssessmentComparison, AssessmentResult, Finding, FindingStatusEvent, TestCase
from app.models.base import utcnow
from app.models.intelligence import AssessmentSchedule, IntelligenceRecord, WebhookEndpoint
from app.security import hash_session_token
from app.services import record_audit

FINDING_STATUSES = {"open", "acknowledged", "in_remediation", "resolved", "accepted_risk"}


def _rows(db: Session, assessment: Assessment) -> list[dict]:
    results = db.scalars(
        select(AssessmentResult).where(AssessmentResult.assessment_id == assessment.id).order_by(AssessmentResult.created_at.asc())
    ).all()
    findings = {finding.result_id: finding for finding in db.scalars(select(Finding).where(Finding.assessment_id == assessment.id)).all()}
    payload = []
    for result in results:
        case = db.get(TestCase, result.test_case_id) if result.test_case_id else None
        finding = findings.get(result.id)
        scenario_meta = (result.evidence_json or {}).get("scenario") or {}
        payload.append(
            {
                "code": scenario_meta.get("result_code") or (case.code if case else finding.stable_key if finding else None),
                "outcome": result.status,
                "severity": finding.severity if finding else None,
            }
        )
    return payload


def assessment_score(db: Session, organisation_id: str, assessment_id: str) -> dict:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    rows = _rows(db, assessment)
    weights = [WEIGHTS.get(row["severity"] or "medium", 4) for row in rows if row["outcome"] == "FAIL"]
    return score_assessment([{"status": row["outcome"]} for row in rows], weights)


def save_baseline(db: Session, organisation_id: str, assessment_id: str, user_id: str, ip_address: str | None) -> Assessment:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if assessment.status != "completed":
        raise AppError(409, "invalid_state", "Only a completed assessment can be a baseline.")
    assessment.is_baseline = True
    record_audit(db, action="baseline_saved", resource_type="assessment", organisation_id=organisation_id, actor_user_id=user_id, resource_id=assessment.id, ip_address=ip_address)
    db.commit()
    db.refresh(assessment)
    return assessment


def rerun_assessment(db: Session, settings: Settings, organisation_id: str, user_id: str, assessment_id: str, ip_address: str | None) -> Assessment:
    source = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if source is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if source.programme_id:
        from app.scenarios.service import launch_programme

        return launch_programme(
            db,
            settings,
            organisation_id=organisation_id,
            user_id=user_id,
            programme_id=source.programme_id,
            name=f"Rerun of {source.name}",
            authorised=True,
            authorisation_note=source.authorisation_note or "Rerun of an authorised programme.",
            ip_address=ip_address,
            trigger_type="regression",
            parent_assessment_id=source.id,
        )
    from app.models.sandboxes import SandboxVersion

    sandbox_id = None
    if source.sandbox_version_id:
        version = db.get(SandboxVersion, source.sandbox_version_id)
        sandbox_id = version.sandbox_id if version else None
    created = plan_assessment(
        db,
        organisation_id=organisation_id,
        user_id=user_id,
        agent_id=source.agent_id,
        name=f"Rerun of {source.name}",
        sandbox_id=sandbox_id,
        categories=list(source.selected_categories or []),
        simulated_role=source.simulated_role,
        authorised=True,
        authorisation_note=source.authorisation_note or "Rerun of an authorised assessment.",
        ip_address=ip_address,
    )
    created.parent_assessment_id = source.id
    created.trigger_type = "regression"
    db.commit()
    return start_assessment(db, settings, organisation_id, created.id)


def compare_assessments(db: Session, organisation_id: str, user_id: str, baseline_id: str, current_id: str, ip_address: str | None) -> dict:
    baseline = db.scalar(select(Assessment).where(Assessment.id == baseline_id, Assessment.organisation_id == organisation_id))
    current = db.scalar(select(Assessment).where(Assessment.id == current_id, Assessment.organisation_id == organisation_id))
    if baseline is None or current is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if baseline.status != "completed" or current.status != "completed":
        raise AppError(409, "invalid_state", "Both assessments must be completed.")
    details = compare_results(_rows(db, baseline), _rows(db, current))
    details["configuration"] = {"baseline": baseline.configuration_json or {}, "current": current.configuration_json or {}}
    existing = db.scalar(
        select(AssessmentComparison).where(
            AssessmentComparison.baseline_assessment_id == baseline.id,
            AssessmentComparison.compared_assessment_id == current.id,
        )
    )
    summary = ", ".join(f"{key} {value}" for key, value in sorted(details["counts"].items()))
    if existing is None:
        existing = AssessmentComparison(
            organisation_id=organisation_id,
            baseline_assessment_id=baseline.id,
            compared_assessment_id=current.id,
            summary=summary,
            details_json=details,
            created_by_user_id=user_id,
        )
        db.add(existing)
    else:
        existing.summary = summary
        existing.details_json = details
    record_audit(db, action="assessment_compared", resource_type="assessment_comparison", organisation_id=organisation_id, actor_user_id=user_id, resource_id=baseline.id, ip_address=ip_address)
    if details["counts"].get("new_vulnerability"):
        from app.commercial.models import AppNotification

        db.add(
            AppNotification(
                organisation_id=organisation_id,
                title="New vulnerability in a regression",
                body=f"{details['counts']['new_vulnerability']} test case result changed to a failure.",
                kind="regression_new",
            )
        )
    db.commit()
    db.refresh(existing)
    return {"id": existing.id, "summary": existing.summary, "details": existing.details_json}


def update_finding(db: Session, organisation_id: str, finding_id: str, user_id: str, status: str | None, note: str, ip_address: str | None) -> Finding:
    finding = db.scalar(select(Finding).where(Finding.id == finding_id, Finding.organisation_id == organisation_id))
    if finding is None:
        raise AppError(404, "not_found", "Finding not found.")
    target = status or finding.status
    if target not in FINDING_STATUSES:
        raise AppError(400, "invalid_status", "That finding status is not supported.")
    previous = finding.status
    finding.status = target
    db.add(
        FindingStatusEvent(
            finding_id=finding.id,
            organisation_id=organisation_id,
            from_status=previous,
            to_status=target,
            note=note,
            actor_user_id=user_id,
        )
    )
    record_audit(db, action="finding_updated", resource_type="finding", organisation_id=organisation_id, actor_user_id=user_id, resource_id=finding.id, ip_address=ip_address, metadata={"from": previous, "to": target})
    db.commit()
    db.refresh(finding)
    return finding


def set_demo_profile(db: Session, organisation_id: str, agent_id: str, profile: str) -> dict:
    if profile not in {"default", "regressed", "remediated"}:
        raise AppError(400, "invalid_profile", "Choose default, regressed, or remediated.")
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.organisation_id == organisation_id, Agent.deleted_at.is_(None)))
    if agent is None or agent.integration_type != "aegis_demo":
        raise AppError(404, "not_found", "Demo agent not found.")
    integration = db.scalar(select(AgentIntegration).where(AgentIntegration.agent_id == agent.id))
    config = dict(integration.config_json or {})
    config["weakness_profile"] = profile
    integration.config_json = config
    db.commit()
    return {"weakness_profile": profile, "simulated": True}


def create_schedule(db: Session, organisation_id: str, user_id: str, name: str, agent_id: str, sandbox_id: str | None, categories: list[str], interval_hours: int, max_runs: int, ip_address: str | None) -> AssessmentSchedule:
    if max_runs < 1 or max_runs > 100 or interval_hours < 1:
        raise AppError(400, "invalid_limit", "Set an interval of at least one hour and a run limit between 1 and 100.")
    from app.services import get_agent

    get_agent(db, organisation_id, agent_id, actor_user_id=user_id, ip_address=ip_address)
    schedule = AssessmentSchedule(
        organisation_id=organisation_id,
        agent_id=agent_id,
        sandbox_id=sandbox_id,
        name=name,
        categories=categories,
        interval_hours=interval_hours,
        max_runs=max_runs,
        runs_completed=0,
        enabled=True,
        created_by_user_id=user_id,
    )
    db.add(schedule)
    db.flush()
    record_audit(db, action="schedule_created", resource_type="assessment_schedule", organisation_id=organisation_id, actor_user_id=user_id, resource_id=schedule.id, ip_address=ip_address, metadata={"max_runs": max_runs})
    db.commit()
    db.refresh(schedule)
    return schedule


def run_schedule(db: Session, settings: Settings, organisation_id: str, user_id: str, schedule_id: str, trigger: str, ip_address: str | None) -> Assessment:
    schedule = db.scalar(select(AssessmentSchedule).where(AssessmentSchedule.id == schedule_id, AssessmentSchedule.organisation_id == organisation_id, AssessmentSchedule.enabled.is_(True)))
    if schedule is None:
        raise AppError(404, "not_found", "Schedule not found.")
    if schedule.runs_completed >= schedule.max_runs:
        raise AppError(409, "limit_reached", "This schedule has reached its execution limit.")
    created = plan_assessment(
        db,
        organisation_id=organisation_id,
        user_id=user_id,
        agent_id=schedule.agent_id,
        name=schedule.name,
        sandbox_id=schedule.sandbox_id,
        categories=list(schedule.categories or []),
        simulated_role=None,
        authorised=True,
        authorisation_note=f"Triggered by {trigger}.",
        ip_address=ip_address,
    )
    created.trigger_type = trigger
    created.schedule_id = schedule.id
    schedule.runs_completed += 1
    record_audit(db, action="assessment_triggered", resource_type="assessment", organisation_id=organisation_id, actor_user_id=user_id, resource_id=created.id, ip_address=ip_address, metadata={"trigger": trigger, "schedule_id": schedule.id})
    db.commit()
    return start_assessment(db, settings, organisation_id, created.id)


def create_webhook(db: Session, organisation_id: str, schedule_id: str) -> str:
    schedule = db.scalar(select(AssessmentSchedule).where(AssessmentSchedule.id == schedule_id, AssessmentSchedule.organisation_id == organisation_id))
    if schedule is None:
        raise AppError(404, "not_found", "Schedule not found.")
    token = secrets.token_urlsafe(24)
    db.add(WebhookEndpoint(organisation_id=organisation_id, schedule_id=schedule.id, token_hash=hash_session_token(token), enabled=True))
    db.commit()
    return token


def trigger_webhook(db: Session, settings: Settings, token: str, ip_address: str | None) -> Assessment:
    endpoint = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.token_hash == hash_session_token(token), WebhookEndpoint.enabled.is_(True)))
    if endpoint is None or endpoint.schedule_id is None:
        raise AppError(401, "unauthenticated", "The webhook token is not valid.")
    schedule = db.get(AssessmentSchedule, endpoint.schedule_id)
    return run_schedule(db, settings, endpoint.organisation_id, schedule.created_by_user_id, schedule.id, "webhook", ip_address)


def intelligence_summary(db: Session, organisation_id: str) -> dict:
    from app.intelligence.remediation_catalogue import BENCHMARKS
    from app.models.intelligence import DatasetVersion, IntelligenceDataset

    approved = db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.approval_status == "approved")).all()
    own = db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.source_organisation_id == organisation_id)).all()
    categories = sorted({(row.record_json or {}).get("test_category") for row in approved if (row.record_json or {}).get("test_category")})
    industries = sorted({(row.record_json or {}).get("industry_category") for row in approved if (row.record_json or {}).get("industry_category")})
    versions = db.scalars(select(DatasetVersion)).all()
    return {
        "approved_records": len(approved),
        "industry_categories": industries,
        "attack_categories": categories,
        "dataset_versions": [{"label": version.version_label, "status": version.status} for version in versions],
        "own_submissions": {"pending_review": sum(1 for row in own if row.validation_status == "pending_review"), "rejected": sum(1 for row in own if row.validation_status == "rejected"), "approved": sum(1 for row in own if row.approval_status == "approved")},
        "benchmarks": [{"code": item["code"], "title": item["title"], "tests": len(item["tests"]), "method": item["method"]} for item in BENCHMARKS],
        "disclaimer": "Benchmark definitions describe the method. They are not a ranking and they do not include other customers' results.",
    }


def approve_record(db: Session, record_id: str, user_is_operator: bool) -> IntelligenceRecord:
    if not user_is_operator:
        raise AppError(403, "forbidden", "Dataset approval is limited to platform review.")
    record = db.get(IntelligenceRecord, record_id)
    if record is None or record.validation_status != "pending_review":
        raise AppError(404, "not_found", "Record not found.")
    record.validation_status = "approved"
    record.approval_status = "approved"
    record_audit(
        db,
        action="intelligence_record_approved",
        resource_type="intelligence_record",
        organisation_id=record.source_organisation_id,
        resource_id=record.id,
        metadata={"validation_status": "approved"},
    )
    db.commit()
    db.refresh(record)
    return record


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
