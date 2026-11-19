from sqlalchemy import select

from app.commercial.jobs import run_job
from app.commercial.models import AssessmentJob
from app.config import get_settings
from tests.test_stage1 import HEADERS, register

NOTE = "I am authorised to test this agent."


def test_viewer_cannot_run_an_assessment(client, db_session):
    register(client, email="viewer@example.com", organisation="Viewer Org")
    me = client.get("/api/v1/auth/me").json()
    from app.models.identity import OrganisationMembership

    membership = db_session.scalar(select(OrganisationMembership).where(OrganisationMembership.user_id == me["user"]["id"]))
    membership.role = "viewer"
    db_session.commit()
    agent = client.post("/api/v1/agents/demo", headers=HEADERS)
    assert agent.status_code == 403


def test_billing_enforcement_rejects_unsubscribed_runs(client):
    register(client, email="billing@example.com", organisation="Billing Org")
    settings = get_settings()
    previous = settings.billing_enforce
    settings.billing_enforce = True
    try:
        agent = client.post("/api/v1/agents/demo", headers=HEADERS)
        assert agent.status_code == 402
    finally:
        settings.billing_enforce = previous


def test_stripe_webhook_requires_a_signature(client):
    response = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Content-Type": "application/json"})
    assert response.status_code == 400


def test_completed_job_is_not_run_twice(client, db_session):
    register(client, email="jobs@example.com", organisation="Jobs Org")
    agent = client.post("/api/v1/agents/demo", headers=HEADERS).json()
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={"agent_id": agent["id"], "name": "Once", "categories": ["instruction_hierarchy"], "authorised": True, "authorisation_note": NOTE},
    )
    started = client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS)
    assert started.status_code == 200
    job = db_session.scalar(select(AssessmentJob).where(AssessmentJob.assessment_id == created.json()["id"]))
    assert job.status == "succeeded"
    attempts = job.attempts
    run_job(db_session, get_settings(), job.id)
    db_session.refresh(job)
    assert job.attempts == attempts


def test_licensed_benchmark_is_withheld_without_a_sample(client):
    register(client, email="license@example.com", organisation="License Org")
    created = client.post("/api/v1/licensed/keys", headers=HEADERS, json={"name": "Read benchmarks"})
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    response = client.get("/api/v1/licensed/benchmarks", headers={"X-Aegis-Api-Key": token})
    assert response.status_code == 200
    body = response.json()
    assert body["published"] == []
    assert body["withheld"]
    assert "evidence" not in response.text.lower() or "raw" not in body
    missing = client.get("/api/v1/licensed/benchmarks")
    assert missing.status_code == 401


def test_admin_overview_is_operator_only(client):
    register(client, email="plain@example.com", organisation="Plain Org")
    assert client.get("/api/v1/admin/overview").status_code == 403
