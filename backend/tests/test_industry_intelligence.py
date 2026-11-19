import copy

from sqlalchemy import select

from app.engine.seed import _ensure_sandbox
from app.models.sandboxes import Industry, Sandbox, SandboxVersion
from app.sandboxes.definitions import SANDBOXES
from app.scenarios import registry
from app.scenarios.evaluation import Observation, evaluate
from app.scenarios.taxonomy import INDUSTRIES
from tests.test_stage1 import HEADERS, register

NOTE = "I am authorised to test this agent in the sandbox."

ACCOUNTING_PROFILE = {
    "industry": "accounting",
    "description": "Bookkeeping assistant for a small practice. It reads invoices and supplier emails from the finance inbox, drafts payment requests for approval, and prepares the monthly management report.",
    "purpose": "Help the accounts clerk process supplier invoices.",
    "responsibilities": ["Process supplier invoices", "Draft payment requests", "Prepare management report"],
    "tools": ["Xero", "Finance inbox"],
    "permissions": ["Read invoices", "Draft payments"],
    "data_types": ["financial", "payment"],
    "authorised_actions": ["Draft payment"],
    "risk_sensitivity": "high",
}


def _demo_agent(client):
    response = client.post("/api/v1/agents/demo", headers=HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def _programme(client, agent_id, profile=None, **options):
    saved = client.put(f"/api/v1/agents/{agent_id}/profile", headers=HEADERS, json=profile or ACCOUNTING_PROFILE)
    assert saved.status_code == 200, saved.text
    created = client.post("/api/v1/programmes", headers=HEADERS, json={"agent_id": agent_id, **options})
    assert created.status_code == 201, created.text
    return created.json()


def _launch(client, programme_id, name="Accounting programme"):
    launched = client.post(
        f"/api/v1/programmes/{programme_id}/launch",
        headers=HEADERS,
        json={"name": name, "authorised": True, "authorisation_note": NOTE},
    )
    assert launched.status_code == 201, launched.text
    return launched.json()["assessment_id"]


def test_library_is_structured_and_covers_required_industries():
    counts = {slug: len(registry.for_industry(slug)) for slug in INDUSTRIES}
    assert counts == {"customer_service": 10, "accounting": 10, "healthcare": 6, "legal": 6, "sales_crm": 6}
    required = {
        "code", "version", "name", "industry", "category", "description", "threat", "risk", "objective", "preconditions",
        "environment", "turns", "secure", "insecure", "evaluation_criteria", "scoring", "remediation",
    }
    for scenario in registry.SCENARIOS.values():
        body = scenario.to_dict()
        assert required <= set(body)
        assert body["preconditions"] and body["turns"] and body["remediation"] and body["evaluation_criteria"]
        assert scenario.environment.sandbox in SANDBOXES
        assert len(scenario.content_hash()) == 64


def test_library_api_lists_and_details_scenarios(client):
    register(client, email="library@example.com", organisation="Library Org")
    index = client.get("/api/v1/scenario-library").json()
    assert {item["slug"] for item in index["industries"]} == set(INDUSTRIES)
    assert len(index["scenarios"]) == 38
    detail = client.get("/api/v1/scenario-library/acct.bank_detail_substitution").json()
    assert detail["threat"] == "AEG-01"
    assert detail["environment"]["sandbox"] == "accounting"
    assert detail["checks"][0]["description"]
    assert client.get("/api/v1/scenario-library/missing.scenario").status_code == 404


def test_profile_analysis_explains_inferred_capabilities(client):
    register(client, email="profile@example.com", organisation="Profile Org")
    analysis = client.post("/api/v1/profile-analysis", headers=HEADERS, json=ACCOUNTING_PROFILE).json()
    keys = {item["key"] for item in analysis["capabilities"]}
    assert {"invoices.process", "payments.initiate", "content.ingest", "finance.reporting"} <= keys
    assert "patients.read" not in keys
    invoice = next(item for item in analysis["capabilities"] if item["key"] == "invoices.process")
    assert invoice["evidence"][0]["term"]
    agent = _demo_agent(client)
    bad = client.put(f"/api/v1/agents/{agent['id']}/profile", headers=HEADERS, json={**ACCOUNTING_PROFILE, "industry": "astrology"})
    assert bad.status_code == 422
    bad_capability = client.put(f"/api/v1/agents/{agent['id']}/profile", headers=HEADERS, json={**ACCOUNTING_PROFILE, "capabilities": ["root.access"]})
    assert bad_capability.status_code == 422


def test_selection_depends_on_responsibilities_not_only_industry(client):
    register(client, email="selection@example.com", organisation="Selection Org")
    agent = _demo_agent(client)
    narrow = {
        **ACCOUNTING_PROFILE,
        "description": "Answers questions about invoice status for clients. It cannot draft or approve payments.",
        "responsibilities": ["Look up invoice status"],
        "tools": [],
        "permissions": ["Read invoices"],
        "authorised_actions": [],
        "capabilities": ["invoices.process"],
    }
    programme = _programme(client, agent["id"], narrow)
    by_code = {entry["code"]: entry for entry in programme["selection"]}
    assert by_code["acct.payment_without_invoice"]["applicable"] is False
    assert "drafts or initiates payments" in by_code["acct.payment_without_invoice"]["reason"]
    assert by_code["acct.invoice_amount_manipulation"]["applicable"] is True
    assert by_code["acct.invoice_amount_manipulation"]["rationale"]

    broad = _programme(client, agent["id"], ACCOUNTING_PROFILE)
    broad_codes = {entry["code"] for entry in broad["selection"] if entry["applicable"]}
    assert "acct.payment_without_invoice" in broad_codes
    assert broad["stats"]["applicable"] > programme["stats"]["applicable"]
    priorities = [entry["priority_points"] for entry in broad["selection"] if entry["applicable"]]
    assert priorities == sorted(priorities, reverse=True)


def test_programme_controls_and_validation(client):
    register(client, email="controls@example.com", organisation="Controls Org")
    agent = _demo_agent(client)
    missing = client.post("/api/v1/programmes", headers=HEADERS, json={"agent_id": agent["id"]})
    assert missing.status_code == 409
    programme = _programme(client, agent["id"])
    focused = client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"intensity": "focused"}).json()
    assert all(entry["priority"] == "P1" for entry in focused["selection"] if entry["selected"])
    not_applicable = next((entry["code"] for entry in focused["selection"] if not entry["applicable"]), None)
    chosen = ["acct.approval_bypass"] + ([not_applicable] if not_applicable else [])
    updated = client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"selected": chosen, "include_generic": True, "generic_categories": ["prompt_injection"]}).json()
    assert updated["stats"]["selected"] == len(chosen)
    assert updated["stats"]["generic"] == 1
    if not_applicable:
        assert updated["stats"]["overrides"] == 1
    unknown = client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"selected": ["cs.not_real"]})
    assert unknown.status_code == 400
    bad_category = client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"generic_categories": ["telepathy"]})
    assert bad_category.status_code == 400
    empty = client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"selected": [], "include_generic": False})
    assert empty.status_code == 200
    refused = client.post(f"/api/v1/programmes/{programme['id']}/launch", headers=HEADERS, json={"name": "Empty", "authorised": True, "authorisation_note": NOTE})
    assert refused.status_code == 400
    unauthorised = client.post(f"/api/v1/programmes/{programme['id']}/launch", headers=HEADERS, json={"name": "No auth", "authorised": False, "authorisation_note": NOTE})
    assert unauthorised.status_code == 400


def test_programme_runs_workflows_and_reports_honestly(client):
    original = copy.deepcopy(SANDBOXES["accounting"]["data"])
    register(client, email="run@example.com", organisation="Run Org")
    agent = _demo_agent(client)
    programme = _programme(client, agent["id"])
    client.patch(f"/api/v1/programmes/{programme['id']}", headers=HEADERS, json={"include_generic": True, "generic_categories": ["prompt_injection"]})
    assessment_id = _launch(client, programme["id"])
    detail = client.get(f"/api/v1/assessments/{assessment_id}").json()
    assert detail["status"] == "completed"
    assert detail["engine"] == "scenario"
    assert detail["is_simulated"] is True
    results = {item["code"]: item for item in detail["results"]}

    injected = results["acct.invoice_embedded_instruction"]
    assert injected["outcome"] == "FAIL"
    roles = [turn["role"] for turn in injected["evidence"]["transcript"]]
    assert "tool" in roles
    assert any(event["tool"] == "search_invoice" and event["allowed"] for event in injected["evidence"]["sandbox_tool_events"])
    assert any(event["tool"] == "approve_payment" and not event["allowed"] for event in injected["evidence"]["sandbox_tool_events"])
    assert injected["evidence"]["reproduction"]["turns"]

    unsupported = results["acct.payment_without_invoice"]
    assert unsupported["outcome"] == "FAIL"
    assert any(change["path"].startswith("payments.") for change in unsupported["evidence"]["state_changes"])

    calculation = results["acct.vat_calculation_integrity"]
    assert calculation["outcome"] == "INCONCLUSIVE"
    assert "generic.prompt_injection" in results

    report = client.get(f"/api/v1/assessments/{assessment_id}/intelligence").json()
    assert report["industry_score"]["applicable_tests"] < report["overall_score"]["applicable_tests"]
    assert report["outcomes"]["INCONCLUSIVE"] >= 1
    assert report["critical"]
    assert report["coverage"]["planned"] == report["coverage"]["recorded"]
    assert report["by_threat"] and report["remediation"]
    findings = client.get("/api/v1/findings").json()
    assert any(item["severity"] == "critical" for item in findings)

    logs = client.get(f"/api/v1/assessments/{assessment_id}/logs").json()
    events = [row["event"] for row in logs]
    assert events[0] == "run_started" and events[-1] == "run_finished"
    assert "tool_call" in events
    assert SANDBOXES["accounting"]["data"] == original


def test_remediated_rerun_shows_resolved_vulnerabilities(client):
    register(client, email="rerun@example.com", organisation="Rerun Org")
    agent = _demo_agent(client)
    programme = _programme(client, agent["id"])
    first = _launch(client, programme["id"], "Baseline")
    client.post(f"/api/v1/agents/{agent['id']}/demo-profile", headers=HEADERS, json={"profile": "remediated"})
    rerun = client.post(f"/api/v1/assessments/{first}/rerun", headers=HEADERS)
    assert rerun.status_code == 200, rerun.text
    second = rerun.json()
    assert second["programme_id"] == programme["id"]
    report = client.get(f"/api/v1/assessments/{second['id']}/intelligence").json()
    assert report["comparison"]["previous_id"] == first
    assert report["comparison"]["counts"].get("resolved_vulnerability", 0) > 0
    assert report["comparison"]["score_delta"] > 0


def test_outcomes_distinguish_failure_inconclusive_and_error():
    scenario = registry.get("acct.approval_bypass")
    unsupported = evaluate(scenario, Observation(tool_channel="unsupported"))
    assert unsupported["outcome"] == "INCONCLUSIVE"
    errored = evaluate(scenario, Observation(error_code="timeout", error_message="The agent did not respond before the timeout."))
    assert errored["outcome"] == "ERROR"
    clean = evaluate(scenario, Observation(tool_channel="supported", replies=["I can't approve payments."]))
    assert clean["outcome"] == "PASS"
    failed = evaluate(scenario, Observation(tool_channel="supported", requests=[{"name": "approve_payment", "arguments": {"pr_id": "PR-9"}}], events=[{"tool": "approve_payment", "allowed": False}]))
    assert failed["outcome"] == "FAIL"
    assert failed["confidence"] == "high"


def test_programmes_are_isolated_between_organisations(client):
    register(client, email="owner-a@example.com", organisation="Org A")
    agent = _demo_agent(client)
    programme = _programme(client, agent["id"])
    client.post("/api/v1/auth/logout", headers=HEADERS)
    register(client, email="owner-b@example.com", organisation="Org B")
    assert client.get(f"/api/v1/programmes/{programme['id']}").status_code == 404
    assert client.get(f"/api/v1/agents/{agent['id']}/profile").status_code == 404
    assert client.get("/api/v1/programmes").json() == []


def test_sandbox_changes_publish_a_new_version(db_session, client):
    industry = db_session.scalar(select(Industry).where(Industry.slug == "healthcare"))
    definition = copy.deepcopy({key: value for key, value in SANDBOXES["healthcare"].items() if key != "tools"})
    definition["tools"] = dict(SANDBOXES["healthcare"]["tools"])
    definition["tools"].pop("update_record_access")
    _ensure_sandbox(db_session, industry, definition)
    db_session.commit()
    sandbox = db_session.scalar(select(Sandbox).where(Sandbox.name == definition["name"]))
    version = db_session.get(SandboxVersion, sandbox.current_version_id)
    assert version.version_number == 2
    assert "Removed tools: update_record_access" in version.changelog
