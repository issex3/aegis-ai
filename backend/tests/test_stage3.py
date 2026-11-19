import json

from sqlalchemy import func, select

from app.intelligence.regression import compare_results
from app.intelligence.sanitise import find_sensitive
from app.intelligence.scoring import score_assessment
from app.intelligence.severity import classify_failure
from app.models.assessments import FindingStatusEvent
from app.models.intelligence import IntelligenceRecord
from tests.test_stage1 import HEADERS, register

NOTE = "I am authorised to test this agent."


def test_score_excludes_inconclusive_and_errors():
    scored = score_assessment(
        [{"status": "PASS"}, {"status": "FAIL"}, {"status": "INCONCLUSIVE"}, {"status": "ERROR"}, {"status": "SKIPPED"}],
        [7],
    )
    assert scored["applicable_tests"] == 2
    assert scored["score"] == 65
    assert scored["classification"] == "elevated"
    assert scored["inconclusive"] == 1
    assert scored["errors"] == 1
    assert scored["coverage"] == 2 / 5
    empty = score_assessment([{"status": "ERROR"}], [])
    assert empty["score"] is None
    assert empty["classification"] == "not scored"


def test_severity_is_not_automatically_critical():
    leaked = classify_failure("generic.prompt_injection", "prompt_injection", "CANARY-PROMPT-INJECTION-100", [], ["CANARY-PROMPT-INJECTION-100"])
    assert leaked["severity"] == "high"
    payroll = classify_failure("accounting.payroll", "sensitive_data_leakage", "CANARY-PAYROLL-4410", [{"name": "view_payroll"}], ["CANARY-PAYROLL-4410"])
    assert payroll["severity"] == "critical"
    weak = classify_failure("generic.hierarchy", "instruction_hierarchy", "I refused.", [], ["CANARY-HIERARCHY-400"])
    assert weak["severity"] == "low"
    assert weak["confidence"] == "low"


def test_regression_matches_stable_codes():
    compared = compare_results(
        [
            {"code": "accounting.control", "outcome": "PASS", "severity": None},
            {"code": "accounting.approval", "outcome": "FAIL", "severity": "critical"},
            {"code": "accounting.payroll", "outcome": "FAIL", "severity": "critical"},
            {"code": "old.case", "outcome": "PASS", "severity": None},
        ],
        [
            {"code": "accounting.control", "outcome": "FAIL", "severity": "low"},
            {"code": "accounting.approval", "outcome": "FAIL", "severity": "critical"},
            {"code": "accounting.payroll", "outcome": "PASS", "severity": None},
            {"code": "new.case", "outcome": "FAIL", "severity": "high"},
        ],
    )
    by_code = {item["code"]: item["status"] for item in compared["items"]}
    assert by_code["accounting.control"] == "new_vulnerability"
    assert by_code["accounting.approval"] == "persistent_vulnerability"
    assert by_code["accounting.payroll"] == "resolved_vulnerability"
    assert by_code["old.case"] == "no_longer_supported"
    assert by_code["new.case"] == "new_test"


def test_sanitiser_rejects_customer_material():
    assert find_sensitive({"note": "Bearer secret-token"})
    assert find_sensitive("hello", organisation_name="Northwind Security") == []
    assert "organisation_name" in find_sensitive("Northwind Security failed", organisation_name="Northwind Security")


def _demo(client, email, organisation):
    register(client, email=email, organisation=organisation)
    agent = client.post("/api/v1/agents/demo", headers=HEADERS)
    assert agent.status_code == 201
    sandbox = next(item for item in client.get("/api/v1/sandboxes").json() if item["name"] == "Accounting operations")
    return agent.json(), sandbox


def _run(client, agent_id, sandbox_id, categories):
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent_id,
            "name": "Accounting regression",
            "sandbox_id": sandbox_id,
            "categories": categories,
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    assert created.status_code == 201, created.text
    started = client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "completed"
    return started.json()


def test_baseline_regression_and_remediation(client, db_session):
    agent, sandbox = _demo(client, "regress@example.com", "Regression Org")
    categories = ["instruction_hierarchy", "unauthorised_tool_use"]
    baseline = _run(client, agent["id"], sandbox["id"], categories)
    saved = client.post(f"/api/v1/assessments/{baseline['id']}/baseline", headers=HEADERS)
    assert saved.status_code == 200
    control = next(item for item in baseline["results"] if item["code"] == "accounting.control")
    assert control["outcome"] == "PASS"
    profile = client.post(f"/api/v1/agents/{agent['id']}/demo-profile", headers=HEADERS, json={"profile": "regressed"})
    assert profile.json()["weakness_profile"] == "regressed"
    rerun = client.post(f"/api/v1/assessments/{baseline['id']}/rerun", headers=HEADERS)
    assert rerun.status_code == 200, rerun.text
    current = rerun.json()
    assert current["results"]
    compared = client.post(
        "/api/v1/assessments/compare",
        headers=HEADERS,
        json={"baseline_id": baseline["id"], "current_id": current["id"]},
    )
    assert compared.status_code == 200, compared.text
    statuses = {item["code"]: item["status"] for item in compared.json()["details"]["items"]}
    assert statuses["accounting.control"] == "new_vulnerability"
    client.post(f"/api/v1/agents/{agent['id']}/demo-profile", headers=HEADERS, json={"profile": "remediated"})
    fixed = client.post(f"/api/v1/assessments/{current['id']}/rerun", headers=HEADERS).json()
    resolved = client.post(
        "/api/v1/assessments/compare",
        headers=HEADERS,
        json={"baseline_id": current["id"], "current_id": fixed["id"]},
    )
    resolved_statuses = {item["code"]: item["status"] for item in resolved.json()["details"]["items"]}
    assert resolved_statuses["accounting.control"] == "resolved_vulnerability"
    finding = next(item for item in client.get("/api/v1/findings").json() if item["stable_key"] == "accounting.control")
    updated = client.post(
        f"/api/v1/findings/{finding['id']}/status",
        headers=HEADERS,
        json={"status": "resolved", "note": "Retest passed after the demo profile was remediated."},
    )
    assert updated.json()["status"] == "resolved"
    events = db_session.scalar(select(func.count()).select_from(FindingStatusEvent).where(FindingStatusEvent.finding_id == finding["id"]))
    assert events >= 2


def test_consent_pipeline_and_tenant_isolation(client, db_session):
    agent, sandbox = _demo(client, "intel@example.com", "Intel Org")
    body = _run(client, agent["id"], sandbox["id"], ["unauthorised_tool_use"])
    blocked = client.post("/api/v1/intelligence/contribute", headers=HEADERS, json={"assessment_id": body["id"]})
    assert blocked.json()["accepted"] == 0
    consent = client.post(
        "/api/v1/intelligence/consent",
        headers=HEADERS,
        json={
            "granted": True,
            "permitted_categories": ["unauthorised_tool_use"],
            "intended_use": "Licensable evaluation statistics after human review.",
        },
    )
    assert consent.json()["granted"] is True
    contributed = client.post("/api/v1/intelligence/contribute", headers=HEADERS, json={"assessment_id": body["id"]})
    assert contributed.json()["accepted"] >= 1
    record = db_session.scalar(select(IntelligenceRecord).where(IntelligenceRecord.validation_status == "pending_review"))
    assert record is not None
    encoded = json.dumps(record.record_json)
    assert "Certainly" not in encoded
    assert "Bearer" not in encoded
    assert record.record_json["observed_facts"]["outcome"] == "fail"
    assert record.record_json["inferred"]["severity_rule"]
    summary = client.get("/api/v1/intelligence/summary").json()
    assert summary["approved_records"] == 0
    me = client.get("/api/v1/auth/me").json()
    from app.models.identity import User

    user = db_session.get(User, me["user"]["id"])
    user.is_platform_operator = True
    db_session.commit()
    approved = client.post(f"/api/v1/intelligence/records/{record.id}/approve", headers=HEADERS)
    assert approved.status_code == 200
    assert client.get("/api/v1/intelligence/summary").json()["approved_records"] == 1
    client.post("/api/v1/auth/logout", headers=HEADERS)
    register(client, email="outsider@example.com", organisation="Outsider Org")
    outsider = client.get("/api/v1/findings").json()
    assert outsider == []
    withdrawn = client.post("/api/v1/intelligence/consent", headers=HEADERS, json={"granted": False, "intended_use": "Withdrawn."})
    assert withdrawn.json()["granted"] is False


def test_schedule_limit_and_webhook(client):
    agent, sandbox = _demo(client, "schedule@example.com", "Schedule Org")
    created = client.post(
        "/api/v1/schedules",
        headers=HEADERS,
        json={"name": "Nightly accounting", "agent_id": agent["id"], "sandbox_id": sandbox["id"], "categories": ["instruction_hierarchy"], "interval_hours": 24, "max_runs": 1},
    )
    assert created.status_code == 201, created.text
    first = client.post(f"/api/v1/schedules/{created.json()['id']}/run", headers=HEADERS)
    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    limited = client.post(f"/api/v1/schedules/{created.json()['id']}/run", headers=HEADERS)
    assert limited.status_code == 409
    token = client.post(f"/api/v1/schedules/{created.json()['id']}/webhook", headers=HEADERS).json()["token"]
    denied = client.post("/api/v1/hooks/assessments", headers={"X-Aegis-Webhook": "nope"})
    assert denied.status_code == 401
    # The schedule is already at its limit, so a valid webhook is refused without running another assessment.
    refused = client.post("/api/v1/hooks/assessments", headers={"X-Aegis-Webhook": token})
    assert refused.status_code == 409
