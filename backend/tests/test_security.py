import json

import pyotp
from sqlalchemy import select

from app.config import get_settings
from app.iam import issue_password_reset
from app.models.agents import AgentCredential
from app.models.identity import Organisation, OrganisationMembership, User
from app.net.ssrf import OutboundBlocked, validate_outbound_url
from app.reports.pdf import build_assessment_pdf
from app.security import decrypt_secret

HEADERS = {"X-Aegis-Client": "web"}
PASSWORD = "CorrectHorse9Battery"  # secret-scan: allow-test-fixture
SECRET = "tenant-a-provider-key-91"  # secret-scan: allow-test-fixture


def _register(client, email, organisation):
    response = client.post(
        "/api/v1/auth/register",
        headers=HEADERS,
        json={
            "full_name": email.split("@")[0].title(),
            "email": email,
            "password": PASSWORD,
            "organisation_name": organisation,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _agent_payload(**overrides):
    payload = {
        "name": "Claims assistant",
        "description": "Handles first-line policy questions for authenticated customers.",
        "integration_type": "openai_compatible",
        "api_endpoint": "https://agents.example.com/v1/claims",
        "model_name": "gpt-4.1-mini",
        "purpose": "Answer policy questions and prepare claim summaries for a human reviewer.",
        "behaviour": "Asks for a policy number, refuses payment instructions, and escalates disputes.",
        "security_boundaries": "Must not reveal other customers' data or change payment details.",
        "secret": SECRET,
    }
    payload.update(overrides)
    return payload


def _pdf_context(**overrides):
    context = {
        "organisation_name": "Northwind",
        "agent_name": "Claims",
        "agent_description": "A helper",
        "assessment_name": "Run 1",
        "assessment_id": "00000000-0000-0000-0000-000000000001",
        "assessment_date": "2026-11-03",
        "integration_type": "openai_compatible",
        "model_name": "demo",
        "sandbox_name": None,
        "sandbox_version": None,
        "scope": "prompt_injection",
        "executive_summary": "No score.",
        "score_text": "Not scored",
        "classification": "not scored",
        "coverage": "0%",
        "applicable": 0,
        "inconclusive": 0,
        "errors": 0,
        "skipped": 0,
        "score_disclaimer": "Internal metric.",
        "severity_counts": {},
        "findings": [],
        "regression": "",
        "limitations": ["Only observable replies were judged."],
    }
    context.update(overrides)
    return context


def test_security_headers_are_set(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_oversized_request_is_rejected(client):
    response = client.post(
        "/api/v1/auth/login",
        headers={**HEADERS, "Content-Length": str(2_000_000)},
        content=b"{" + b"x" * 2_000_000 + b"}",
    )
    assert response.status_code == 413


def test_pdf_markup_does_not_open_network_connections(monkeypatch):
    opened = []

    def fake_create_connection(*args, **kwargs):
        opened.append(args)
        raise AssertionError("PDF generation must not open network connections")

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    hostile = '<img src="http://169.254.169.254/latest/meta-data/" /> <script>alert(1)</script>'
    pdf = build_assessment_pdf(
        _pdf_context(
            findings=[
                {
                    "title": hostile,
                    "severity": "high",
                    "confidence": "high",
                    "description": hostile,
                    "business_impact": hostile,
                    "expected_behaviour": "refuse",
                    "actual_behaviour": hostile,
                    "reproduction_steps": hostile,
                    "evidence": hostile,
                    "remediation": hostile,
                    "simulated": False,
                    "severity_rule": "test",
                }
            ]
        )
    )
    assert opened == []
    assert pdf.startswith(b"%PDF")
    assert b"<img src=" not in pdf


def test_ssrf_still_blocks_metadata_and_private_addresses():
    for url in (
        "https://169.254.169.254/latest",
        "https://127.0.0.1/v1",
        "https://10.0.0.5/v1",
        "https://metadata.google.internal/v1",
    ):
        try:
            validate_outbound_url(url)
        except OutboundBlocked:
            continue
        raise AssertionError(url)


def test_tenant_isolation_across_resources(client):
    owner = _register(client, "owner-a@example.com", "Org A")
    created = client.post("/api/v1/agents", headers=HEADERS, json=_agent_payload())
    assert created.status_code == 201, created.text
    agent_id = created.json()["id"]
    assert SECRET not in created.text
    demo = client.post("/api/v1/agents/demo", headers=HEADERS)
    assert demo.status_code == 201
    client.post("/api/v1/auth/logout", headers=HEADERS)

    _register(client, "owner-b@example.com", "Org B")
    assert client.get(f"/api/v1/agents/{agent_id}").status_code == 404
    assert client.get("/api/v1/agents").json() == []
    stolen_secret = client.put(f"/api/v1/agents/{agent_id}/credential", headers=HEADERS, json={"secret": "bbbbbbbbbbbb"})
    assert stolen_secret.status_code == 404
    assert client.get("/api/v1/findings").json() == []
    assert client.get("/api/v1/reports").json() == []
    assert client.get("/api/v1/programmes").json() == []
    export = client.get("/api/v1/organisations/export")
    body = export.json()
    assert owner["organisation"]["id"] not in json.dumps(body)
    assert body["organisation"]["name"] != "Org A"


def test_origin_change_revokes_credential_and_requires_admin(client, db_session):
    _register(client, "owner@example.com", "Origin Org")
    created = client.post("/api/v1/agents", headers=HEADERS, json=_agent_payload())
    agent_id = created.json()["id"]
    invite = client.post("/api/v1/members", headers=HEADERS, json={"email": "analyst@example.com", "role": "analyst"})
    assert invite.status_code == 201, invite.text
    token = invite.json()["invite_token"]
    client.post("/api/v1/auth/logout", headers=HEADERS)
    joined = client.post(
        "/api/v1/auth/register",
        headers=HEADERS,
        json={
            "full_name": "Analyst",
            "email": "analyst@example.com",
            "password": PASSWORD,
            "organisation_name": "Ignored",
            "invite_token": token,
        },
    )
    assert joined.status_code == 201, joined.text
    assert joined.json()["role"] == "analyst"
    denied = client.patch(
        f"/api/v1/agents/{agent_id}",
        headers=HEADERS,
        json=_agent_payload(api_endpoint="https://attacker.example.com/v1/steal", secret=None),
    )
    assert denied.status_code == 403
    client.post("/api/v1/auth/logout", headers=HEADERS)
    login = client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "owner@example.com", "password": PASSWORD})
    assert login.status_code == 200
    rotated = client.patch(
        f"/api/v1/agents/{agent_id}",
        headers=HEADERS,
        json=_agent_payload(api_endpoint="https://attacker.example.com/v1/steal", secret=None),
    )
    assert rotated.status_code == 200
    assert rotated.json()["credential"]["configured"] is False
    row = db_session.scalar(select(AgentCredential).where(AgentCredential.agent_id == agent_id, AgentCredential.deleted_at.is_(None)))
    assert row is None


def test_mfa_enrolment_and_challenge(client):
    _register(client, "mfa@example.com", "MFA Org")
    setup = client.post("/api/v1/auth/mfa/setup", headers=HEADERS)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    confirm = client.post("/api/v1/auth/mfa/confirm", headers=HEADERS, json={"code": pyotp.TOTP(secret).now()})
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["enabled"] is True
    assert len(confirm.json()["recovery_codes"]) == 8
    client.post("/api/v1/auth/logout", headers=HEADERS)
    first = client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "mfa@example.com", "password": PASSWORD})
    assert first.status_code == 200
    assert first.json()["mfa_required"] is True
    challenge = first.json()["challenge_id"]
    assert client.get("/api/v1/auth/me").status_code == 401
    verified = client.post("/api/v1/auth/mfa/verify", headers=HEADERS, json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()})
    assert verified.status_code == 200, verified.text
    assert verified.json()["user"]["mfa_enabled"] is True
    assert client.get("/api/v1/auth/me").status_code == 200


def test_password_reset_revokes_access(client, db_session):
    _register(client, "reset@example.com", "Reset Org")
    assert client.get("/api/v1/auth/me").status_code == 200
    forgot = client.post("/api/v1/auth/forgot-password", headers=HEADERS, json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    unknown = client.post("/api/v1/auth/forgot-password", headers=HEADERS, json={"email": "missing@example.com"})
    assert unknown.status_code == 200
    token = issue_password_reset(db_session, get_settings(), "reset@example.com", "127.0.0.1")
    assert token
    reset = client.post(
        "/api/v1/auth/reset-password",
        headers=HEADERS,
        json={"token": token, "new_password": "NewCorrectHorse10"},
    )
    assert reset.status_code == 200, reset.text
    assert client.get("/api/v1/auth/me").status_code == 401
    old = client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "reset@example.com", "password": PASSWORD})
    assert old.status_code == 401
    new = client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "reset@example.com", "password": "NewCorrectHorse10"})
    assert new.status_code == 200


def test_privilege_escalation_is_blocked(client):
    _register(client, "owner@example.com", "Priv Org")
    invite = client.post("/api/v1/members", headers=HEADERS, json={"email": "viewer@example.com", "role": "viewer"})
    token = invite.json()["invite_token"]
    client.post("/api/v1/auth/logout", headers=HEADERS)
    client.post(
        "/api/v1/auth/register",
        headers=HEADERS,
        json={
            "full_name": "Viewer",
            "email": "viewer@example.com",
            "password": PASSWORD,
            "organisation_name": "Ignored",
            "invite_token": token,
        },
    )
    assert client.post("/api/v1/agents", headers=HEADERS, json=_agent_payload()).status_code == 403
    assert client.get("/api/v1/audit-events").status_code == 403
    assert client.post("/api/v1/members", headers=HEADERS, json={"email": "other@example.com", "role": "owner"}).status_code == 403


def test_last_owner_cannot_be_removed(client, db_session):
    session = _register(client, "solo@example.com", "Solo Org")
    membership = db_session.scalar(select(OrganisationMembership).where(OrganisationMembership.user_id == session["user"]["id"]))
    denied = client.delete(f"/api/v1/members/{membership.id}", headers=HEADERS)
    assert denied.status_code == 400


def test_credentials_use_tenant_bound_ciphertext(client, db_session):
    _register(client, "keys@example.com", "Key Org")
    created = client.post("/api/v1/agents", headers=HEADERS, json=_agent_payload())
    stored = db_session.scalar(select(AgentCredential).where(AgentCredential.agent_id == created.json()["id"]))
    assert stored.ciphertext.startswith("v2:")
    org = db_session.scalar(select(Organisation).where(Organisation.name == "Key Org"))
    plaintext = decrypt_secret(get_settings(), stored.ciphertext, org.id)
    assert plaintext == SECRET
    try:
        decrypt_secret(get_settings(), stored.ciphertext, "00000000-0000-0000-0000-000000000099")
    except Exception:
        return
    raise AssertionError("foreign organisation decrypted a tenant ciphertext")


def test_export_omits_secrets_and_delete_removes_tenant(client, db_session):
    _register(client, "privacy@example.com", "Privacy Org")
    created = client.post("/api/v1/agents", headers=HEADERS, json=_agent_payload())
    exported = client.get("/api/v1/organisations/export")
    assert exported.status_code == 200
    text = exported.text
    assert SECRET not in text
    assert "ciphertext" not in text
    deleted = client.post("/api/v1/organisations/delete", headers=HEADERS)
    assert deleted.status_code == 200, deleted.text
    assert client.get("/api/v1/auth/me").status_code == 401
    remaining = db_session.scalar(select(AgentCredential).where(AgentCredential.agent_id == created.json()["id"]))
    if remaining is not None:
        assert remaining.ciphertext.startswith("deleted:")


def test_licensed_keys_can_be_listed_and_revoked(client):
    _register(client, "license@example.com", "License Org")
    created = client.post("/api/v1/licensed/keys", headers=HEADERS, json={"name": "Benchmarks"})
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    key_id = created.json()["id"]
    listing = client.get("/api/v1/licensed/keys")
    assert listing.status_code == 200
    assert listing.json()[0]["prefix"] == token[:8]
    assert token not in listing.text
    allowed = client.get("/api/v1/licensed/benchmarks", headers={"x-aegis-api-key": token})
    assert allowed.status_code == 200
    revoked = client.delete(f"/api/v1/licensed/keys/{key_id}", headers=HEADERS)
    assert revoked.status_code == 200
    denied = client.get("/api/v1/licensed/benchmarks", headers={"x-aegis-api-key": token})
    assert denied.status_code == 401


def test_account_lockout_after_repeated_failures(client, monkeypatch):
    _register(client, "lock@example.com", "Lock Org")
    client.post("/api/v1/auth/logout", headers=HEADERS)
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_lockout_threshold", 3)
    monkeypatch.setattr(settings, "auth_rate_limit_enabled", False)
    for _ in range(3):
        client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "lock@example.com", "password": "wrong-password-1"})
    locked = client.post("/api/v1/auth/login", headers=HEADERS, json={"email": "lock@example.com", "password": PASSWORD})
    assert locked.status_code == 429
