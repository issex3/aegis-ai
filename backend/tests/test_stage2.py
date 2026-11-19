import json

from sqlalchemy import select

from app.engine.runner import execute_assessment
from app.integrations.base import AgentRequest
from app.integrations.openai_chat import complete
from app.models.assessments import Assessment, Finding
from app.models.base import ensure_utc, utcnow
from app.net.ssrf import OutboundBlocked, validate_outbound_url
from app.sandboxes.definitions import SANDBOXES
from app.sandboxes.runtime import SandboxSession
from tests.test_stage1 import HEADERS, register

NOTE = "I am authorised to test this agent."


def demo_agent(client):
    response = client.post("/api/v1/agents/demo", headers=HEADERS)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["adapter_status"] == "demo"
    assert body["credential"]["configured"] is False
    return body


def run_sandbox(client, sandbox_name: str):
    register(client, email=f"{sandbox_name.split()[0].lower()}@example.com", organisation=f"{sandbox_name} Org")
    agent = demo_agent(client)
    sandboxes = client.get("/api/v1/sandboxes").json()
    sandbox = next(item for item in sandboxes if item["name"] == sandbox_name)
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": f"{sandbox_name} assessment",
            "sandbox_id": sandbox["id"],
            "categories": [],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    assert created.status_code == 201, created.text
    started = client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS)
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "completed"
    assert body["is_simulated"] is True
    outcomes = {item["outcome"] for item in body["results"]}
    assert "PASS" in outcomes
    assert "FAIL" in outcomes
    assert "ERROR" not in outcomes
    for item in body["results"]:
        assert item["outcome"] != "PASS" or not item["evidence"].get("error_code")
        blob = json.dumps(item["evidence"])
        assert "Bearer" not in blob
    findings = client.get("/api/v1/findings").json()
    assert findings
    assert all(item["title"] for item in findings)
    return body


def test_ssrf_blocks_private_and_alternate_forms():
    blocked = [
        "http://example.com/v1",
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://10.1.2.3/v1",
        "https://192.168.1.9/v1",
        "https://172.16.0.4/v1",
        "https://169.254.169.254/latest",
        "https://[::1]/v1",
        "https://[::ffff:127.0.0.1]/v1",
        "https://2130706433/v1",
        "https://0177.0.0.1/v1",
        "https://metadata.google.internal/v1",
        "https://example.com:22/v1",
        "https://user:pass@example.com/v1",
    ]
    for url in blocked:
        try:
            validate_outbound_url(url)
        except OutboundBlocked:
            continue
        raise AssertionError(url)


def test_ssrf_rechecks_dns(monkeypatch):
    calls = {"count": 0}

    def fake_getaddrinfo(host, port, *args, **kwargs):
        calls["count"] += 1
        address = "93.184.216.34" if calls["count"] == 1 else "127.0.0.1"
        return [(2, 1, 6, "", (address, port))]

    monkeypatch.setattr("app.net.ssrf._ORIGINAL_GETADDRINFO", fake_getaddrinfo)
    validate_outbound_url("https://example.com/v1")
    try:
        validate_outbound_url("https://example.com/v1")
    except OutboundBlocked:
        return
    raise AssertionError("rebinding was accepted")


def test_openai_adapter_normalises_and_retries():
    attempts = {"count": 0}

    def transport(url, headers, body):
        attempts["count"] += 1
        assert headers["Authorization"] == "Bearer test-secret-value"
        assert "test-secret-value" not in body.decode()
        if attempts["count"] == 1:
            return 429, b"", 0
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "no",
                        "tool_calls": [{"function": {"name": "approve_payment", "arguments": "{\"pr_id\":\"PR-9\"}"}}],
                    }
                }
            ]
        }
        return 200, json.dumps(payload).encode(), 0

    result = complete(
        AgentRequest(
            endpoint="https://example.com/v1",
            model="demo",
            credential="test-secret-value",
            timeout_seconds=5,
            max_output_tokens=32,
            temperature=0,
            messages=[{"role": "user", "content": "ping"}],
            tools=[],
            config={},
        ),
        sleeper=lambda _seconds: None,
        transport=transport,
    )
    assert attempts["count"] == 2
    assert result.text == "no"
    assert result.tool_calls[0].name == "approve_payment"
    assert result.tool_calls[0].arguments["pr_id"] == "PR-9"
    assert result.error_code is None


def test_openai_malformed_is_not_a_pass():
    def transport(_url, _headers, _body):
        return 200, b"not-json", 0

    result = complete(
        AgentRequest(
            endpoint="https://example.com/v1",
            model="demo",
            credential="x12345678",
            timeout_seconds=5,
            max_output_tokens=32,
            temperature=None,
            messages=[{"role": "user", "content": "ping"}],
            tools=[],
            config={},
        ),
        sleeper=lambda _seconds: None,
        transport=transport,
    )
    assert result.error_code == "malformed_response"


def test_every_sandbox_tool_allow_and_deny():
    expectations = {
        "accounting": [
            ("accounts_clerk", "search_invoice", {"inv_id": "INV-100"}, True),
            ("accounts_clerk", "approve_payment", {"pr_id": "PR-9"}, False),
            ("accounts_clerk", "view_payroll", {"emp_id": "EMP-1"}, False),
            ("accounts_clerk", "retrieve_customer_record", {"cli_id": "CLI-2"}, False),
            ("finance_approver", "approve_payment", {"pr_id": "PR-9"}, True),
            ("finance_approver", "update_supplier_details", {"sup_id": "SUP-1"}, True),
            ("payroll_officer", "view_payroll", {"emp_id": "EMP-1"}, True),
        ],
        "legal": [
            ("legal_assistant", "search_case", {"case_id": "CASE-1"}, True),
            ("legal_assistant", "share_document", {"doc_id": "DOC-1"}, False),
            ("legal_assistant", "search_case", {"case_id": "CASE-2"}, False),
            ("solicitor", "share_document", {"doc_id": "DOC-1"}, True),
            ("solicitor", "change_document_permissions", {"doc_id": "DOC-1"}, True),
        ],
        "retail": [
            ("support_agent", "search_order", {"ord_id": "ORD-1"}, True),
            ("support_agent", "issue_refund_request", {"ord_id": "ORD-2"}, False),
            ("support_agent", "modify_order", {"ord_id": "ORD-1"}, False),
            ("support_agent", "retrieve_customer", {"cus_id": "CUS-2"}, False),
            ("store_manager", "modify_order", {"ord_id": "ORD-1"}, True),
            ("store_manager", "update_delivery_information", {"ord_id": "ORD-1"}, True),
            ("support_agent", "view_inventory", {"sku": "SKU-MUG"}, True),
        ],
    }
    for slug, checks in expectations.items():
        assert SANDBOXES[slug]["tools"]
        for role, tool, arguments, allowed in checks:
            session = SandboxSession(slug, role)
            event = session.call(tool, arguments)
            assert event.allowed is allowed, (slug, role, tool, event.policy)
            assert event.role == role
            assert event.policy


def test_accounting_legal_and_retail_demo_assessments(client):
    accounting = run_sandbox(client, "Accounting operations")
    assert any(item["code"].startswith("accounting.") and item["outcome"] == "FAIL" for item in accounting["results"])
    client.post("/api/v1/auth/logout", headers=HEADERS)
    legal = run_sandbox(client, "Legal matter workspace")
    assert any(item["code"].startswith("legal.") and item["outcome"] == "FAIL" for item in legal["results"])
    client.post("/api/v1/auth/logout", headers=HEADERS)
    retail = run_sandbox(client, "Retail support desk")
    assert any(item["code"].startswith("retail.") and item["outcome"] == "FAIL" for item in retail["results"])


def test_unimplemented_adapter_does_not_run(client):
    register(client, email="blocked@example.com", organisation="Blocked Org")
    from tests.test_stage1 import agent_payload

    created = client.post("/api/v1/agents", headers=HEADERS, json=agent_payload(integration_type="n8n", secret=None))
    assert created.status_code == 422
    created = client.post("/api/v1/agents", headers=HEADERS, json=agent_payload(integration_type="anthropic", secret=None))
    assert created.status_code == 201
    connection = client.post(f"/api/v1/agents/{created.json()['id']}/connection-test", headers=HEADERS)
    assert connection.status_code == 200
    assert connection.json()["ok"] is False
    plan = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": created.json()["id"],
            "name": "Should not run",
            "categories": ["prompt_injection"],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    assert plan.status_code == 409


def test_cancel_pending_assessment(client, db_session):
    register(client, email="cancel@example.com", organisation="Cancel Org")
    agent = demo_agent(client)
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": "Cancel me",
            "categories": ["prompt_injection"],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    assessment_id = created.json()["id"]
    cancelled = client.post(f"/api/v1/assessments/{assessment_id}/cancel", headers=HEADERS)
    assert cancelled.json()["status"] == "cancelled"
    row = db_session.get(Assessment, assessment_id)
    row.status = "pending"
    row.cancel_requested = True
    row.completed_at = None
    db_session.commit()
    from app.config import get_settings

    execute_assessment(db_session, get_settings(), assessment_id)
    db_session.expire_all()
    detail = client.get(f"/api/v1/assessments/{assessment_id}").json()
    assert detail["results"]
    assert all(item["outcome"] == "SKIPPED" for item in detail["results"])
    assert detail["status"] == "cancelled"


def test_timeout_is_not_a_pass(client, monkeypatch):
    register(client, email="timeout@example.com", organisation="Timeout Org")
    agent = demo_agent(client)
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": "Timeout",
            "categories": ["instruction_hierarchy"],
            "authorised": False,
            "authorisation_note": NOTE,
        },
    )
    assert created.status_code == 400
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": "Timeout",
            "categories": ["instruction_hierarchy"],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    from app.integrations.base import AdapterResult

    monkeypatch.setattr(
        "app.engine.runner.run_adapter",
        lambda *_args, **_kwargs: AdapterResult(error_code="timeout", error_message="The agent did not respond before the timeout."),
    )
    started = client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS)
    assert all(item["outcome"] == "ERROR" for item in started.json()["results"])
    assert "PASS" not in {item["outcome"] for item in started.json()["results"]}


def test_other_organisation_cannot_read_results(client):
    register(client, email="owner@example.com", organisation="Owner Org")
    agent = demo_agent(client)
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": "Private",
            "categories": ["prompt_injection"],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS)
    client.post("/api/v1/auth/logout", headers=HEADERS)
    register(client, email="other@example.com", organisation="Other Org")
    hidden = client.get(f"/api/v1/assessments/{created.json()['id']}")
    assert hidden.status_code == 404
    assert client.get("/api/v1/findings").json() == []


def test_findings_are_persisted(client, db_session):
    body = run_sandbox(client, "Accounting operations")
    failed = [item for item in body["results"] if item["outcome"] == "FAIL"]
    rows = db_session.scalars(select(Finding).where(Finding.organisation_id.is_not(None))).all()
    assert len(rows) >= len(failed)
    assert all(ensure_utc(row.created_at) <= utcnow() for row in rows)
