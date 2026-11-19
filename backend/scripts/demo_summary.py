"""Run the three sandbox assessments against the local demo agent and print outcomes."""

from fastapi.testclient import TestClient

from app.engine.seed import ensure_platform_content
from app.database import SessionLocal
from app.main import app

HEADERS = {"X-Aegis-Client": "web"}
NOTE = "I am authorised to test this agent."


def main() -> None:
    session = SessionLocal()
    ensure_platform_content(session)
    session.close()
    client = TestClient(app)
    registered = client.post(
        "/api/v1/auth/register",
        headers=HEADERS,
        json={
            "full_name": "Demo Operator",
            "email": "demo-stage2@example.com",
            "password": "CorrectHorse9Battery",
            "organisation_name": "Stage 2 Demo",
        },
    )
    if registered.status_code == 409:
        logged_in = client.post(
            "/api/v1/auth/login",
            headers=HEADERS,
            json={"email": "demo-stage2@example.com", "password": "CorrectHorse9Battery"},
        )
        logged_in.raise_for_status()
    agent = client.post("/api/v1/agents/demo", headers=HEADERS).json()
    sandboxes = {item["name"]: item["id"] for item in client.get("/api/v1/sandboxes").json()}
    for name in ("Accounting operations", "Legal matter workspace", "Retail support desk"):
        created = client.post(
            "/api/v1/assessments/plan",
            headers=HEADERS,
            json={
                "agent_id": agent["id"],
                "name": name,
                "sandbox_id": sandboxes[name],
                "categories": [],
                "authorised": True,
                "authorisation_note": NOTE,
            },
        ).json()
        detail = client.post(f"/api/v1/assessments/{created['id']}/run", headers=HEADERS).json()
        print(f"\n{name} [{detail['status']}] simulated={detail['is_simulated']}")
        for item in detail["results"]:
            if item["code"] and not item["code"].startswith("generic."):
                print(f"  {item['outcome']:12} {item['code']}")


if __name__ == "__main__":
    main()
