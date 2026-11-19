"""Celery entrypoint. The task loads the durable job row and runs the same function as local execution."""

import os

from celery import Celery

from app.config import get_settings
from app.database import SessionLocal

settings = get_settings()
celery_app = Celery("aegis", broker=settings.celery_broker_url or os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0")
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1


@celery_app.task(name="aegis.run_assessment", bind=True, max_retries=2)
def run_assessment_task(self, job_id: str) -> str:
    session = SessionLocal()
    try:
        from app.commercial.jobs import run_job

        run_job(session, get_settings(), job_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
    finally:
        session.close()
    return job_id
