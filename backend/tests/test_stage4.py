import re
import zlib

from app.reports.pdf import build_assessment_pdf
from tests.test_stage1 import HEADERS, register


def pdf_text(data: bytes) -> str:
    parts = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = match.group(1)
        try:
            parts.append(zlib.decompress(raw).decode("latin-1", errors="ignore"))
        except zlib.error:
            parts.append(raw.decode("latin-1", errors="ignore"))
    return "\n".join(parts)

NOTE = "I am authorised to test this agent."


def test_pdf_labels_observations_and_limits():
    pdf = build_assessment_pdf(
        {
            "organisation_name": "Northwind Security",
            "agent_name": "Claims assistant",
            "agent_description": "Answers policy questions.",
            "assessment_name": "Boundary review",
            "assessment_id": "assessment-1",
            "assessment_date": "2026-11-01T00:00:00+00:00",
            "integration_type": "aegis_demo",
            "model_name": "aegis-demo-1",
            "sandbox_name": "Accounting operations",
            "sandbox_version": 1,
            "scope": "prompt_injection",
            "executive_summary": "One failure was observed.",
            "score_text": "65",
            "classification": "elevated",
            "coverage": "40%",
            "applicable": 2,
            "inconclusive": 1,
            "errors": 0,
            "skipped": 0,
            "score_disclaimer": "Internal assessment metric. Not a certification.",
            "severity_counts": {"high": 1},
            "findings": [
                {
                    "title": "Invoice instruction manipulation",
                    "severity": "high",
                    "confidence": "high",
                    "description": "The marker was observed.",
                    "business_impact": "A boundary was crossed.",
                    "expected_behaviour": "Refuse.",
                    "actual_behaviour": "The marker was repeated.",
                    "reproduction_steps": "Send the invoice text.",
                    "evidence": "Observable response contained the marker.",
                    "remediation": "Separate instructions from records.",
                    "severity_rule": "boundary_category",
                    "simulated": True,
                }
            ],
            "regression": "",
            "limitations": ["Sandbox tools use fictional records."],
        }
    )
    assert pdf.startswith(b"%PDF")
    text = pdf.decode("latin-1", errors="ignore")
    assert "Northwind Security" in text
    assert "not a penetration test" in text
    assert "Observed fact" in text
    assert "Inferred classification" in text
    assert b"%PDF" == pdf[:4]


def _completed(client):
    register(client, email="report@example.com", organisation="Report Org")
    agent = client.post("/api/v1/agents/demo", headers=HEADERS).json()
    sandbox = next(item for item in client.get("/api/v1/sandboxes").json() if item["name"] == "Accounting operations")
    created = client.post(
        "/api/v1/assessments/plan",
        headers=HEADERS,
        json={
            "agent_id": agent["id"],
            "name": "Reportable",
            "sandbox_id": sandbox["id"],
            "categories": ["instruction_hierarchy"],
            "authorised": True,
            "authorisation_note": NOTE,
        },
    )
    detail = client.post(f"/api/v1/assessments/{created.json()['id']}/run", headers=HEADERS).json()
    return detail


def test_report_access_is_limited_to_the_organisation(client):
    detail = _completed(client)
    created = client.post(f"/api/v1/assessments/{detail['id']}/reports", headers=HEADERS)
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]
    downloaded = client.get(f"/api/v1/reports/{report_id}/download")
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF")
    assert "Report Org" in downloaded.content.decode("latin-1", errors="ignore")
    catalogue = client.get("/api/v1/sandbox-catalogue").json()
    assert any(item["availability"] == "available" and item["name"] == "Accounting operations" for item in catalogue["available"])
    assert all(item["status"] == "not_available" for item in catalogue["planned"])
    assert "Insurance" in {item["name"] for item in catalogue["planned"]}
    assert "Healthcare" not in {item["name"] for item in catalogue["planned"]}
    assert any(item["name"] == "Outpatient clinic services" for item in catalogue["available"])
    onboarding = client.get("/api/v1/onboarding").json()
    assert onboarding["steps"][0]["done"] is True
    assert any(step["id"] == "assessment" and step["done"] for step in onboarding["steps"])
    client.post("/api/v1/auth/logout", headers=HEADERS)
    register(client, email="other-report@example.com", organisation="Other Report Org")
    hidden = client.get(f"/api/v1/reports/{report_id}/download")
    assert hidden.status_code == 404
    removed = client.delete(f"/api/v1/reports/{report_id}", headers=HEADERS)
    assert removed.status_code == 404


def test_owner_can_delete_a_report(client):
    detail = _completed(client)
    created = client.post(f"/api/v1/assessments/{detail['id']}/reports", headers=HEADERS)
    report_id = created.json()["id"]
    regenerated = client.post(f"/api/v1/reports/{report_id}/regenerate", headers=HEADERS)
    assert regenerated.status_code == 200
    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=HEADERS)
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/reports/{report_id}/download").status_code == 404
