"""Simulation Lab sessions use the existing SandboxSession engine."""

from app.sandboxes.lab import clear_store_for_tests
from tests.test_stage1 import HEADERS, register


def test_accounting_lab_session_tool_has_observable_consequence(client):
    clear_store_for_tests()
    register(client)
    sandboxes = client.get("/api/v1/sandboxes").json()
    accounting = next(item for item in sandboxes if item["name"].startswith("Accounting"))

    created = client.post(
        f"/api/v1/sandboxes/{accounting['id']}/lab/sessions",
        headers=HEADERS,
        json={"role": "accounts_clerk"},
    )
    assert created.status_code == 201, created.text
    session = created.json()
    assert session["slug"] == "accounting"
    assert session["role"] == "accounts_clerk"
    assert session["state"]["payments"]["PR-9"]["status"] == "draft"
    assert session["stats"]["tool_calls"] == 0

    denied = client.post(
        f"/api/v1/sandboxes/{accounting['id']}/lab/sessions/{session['id']}/tools",
        headers=HEADERS,
        json={"tool": "approve_payment", "arguments": {"pr_id": "PR-9"}},
    )
    assert denied.status_code == 200, denied.text
    denied_body = denied.json()
    assert denied_body["last_event"]["allowed"] is False
    assert denied_body["state"]["payments"]["PR-9"]["status"] == "draft"
    assert denied_body["stats"]["denied"] == 1

    drafted = client.post(
        f"/api/v1/sandboxes/{accounting['id']}/lab/sessions/{session['id']}/tools",
        headers=HEADERS,
        json={"tool": "create_payment_request", "arguments": {"inv_id": "INV-100"}},
    )
    assert drafted.status_code == 200, drafted.text
    drafted_body = drafted.json()
    assert drafted_body["last_event"]["allowed"] is True
    assert drafted_body["state"]["payments"]["PR-NEW"]["status"] == "draft"
    assert drafted_body["stats"]["allowed"] >= 1

    # Switch to approver via a new session — role is fixed for a session.
    approver = client.post(
        f"/api/v1/sandboxes/{accounting['id']}/lab/sessions",
        headers=HEADERS,
        json={"role": "finance_approver"},
    ).json()
    approved = client.post(
        f"/api/v1/sandboxes/{approver['sandbox_id']}/lab/sessions/{approver['id']}/tools",
        headers=HEADERS,
        json={"tool": "approve_payment", "arguments": {"pr_id": "PR-9"}},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"]["payments"]["PR-9"]["status"] == "approved"

    catalogue = client.get("/api/v1/sandbox-catalogue").json()
    item = next(row for row in catalogue["available"] if row["id"] == accounting["id"])
    assert item["slug"] == "accounting"
    assert item["scenario_count"] >= 7
    assert "search_invoice" in item["tools"]
    assert any(row["key"] == "financial" for row in item["data_classes"])
