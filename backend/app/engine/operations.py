"""Assessment planning, connection tests, and catalogue reads."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.commercial.billing import enforce_assessment_limit
from app.commercial.jobs import enqueue_job
from app.engine.catalog import CATEGORIES, cases_for
from app.errors import AppError
from app.integrations.base import AgentRequest
from app.integrations.registry import adapter_availability, run_adapter
from app.models.agents import Agent
from app.models.assessments import Assessment, AssessmentResult, TestCase
from app.models.base import utcnow
from app.models.sandboxes import Sandbox, SandboxDataset, SandboxTool, SandboxVersion, SandboxWorkflow
from app.sandboxes.definitions import SANDBOXES
from app.services import get_agent, load_credential_secret, record_audit

def _slug_for(sandbox: Sandbox | None) -> str | None:
    if sandbox is None:
        return None
    for slug, definition in SANDBOXES.items():
        if definition["name"] == sandbox.name:
            return slug
    return None


def visible_sandbox(db: Session, organisation_id: str, sandbox_id: str) -> Sandbox:
    sandbox = db.get(Sandbox, sandbox_id)
    if sandbox is None or (sandbox.organisation_id not in {None, organisation_id}):
        raise AppError(404, "not_found", "Sandbox not found.")
    return sandbox


def preview_cases(sandbox_slug: str | None, categories: list[str]) -> list[dict]:
    chosen = set(categories or CATEGORIES)
    return [
        {
            "code": case.code,
            "title": case.title,
            "category": case.category,
            "severity": case.severity,
            "requires_tools": case.requires_tools,
            "sandbox": case.sandbox,
        }
        for case in cases_for(sandbox_slug, chosen)
    ]


def create_demo_agent(db: Session, *, organisation_id: str, user_id: str, ip_address: str | None):
    from app.commercial.billing import enforce_agent_limit
    from app.config import get_settings
    from app.models.agents import AgentIntegration
    from app.services import to_agent_out

    enforce_agent_limit(db, get_settings(), organisation_id)

    agent = Agent(
        organisation_id=organisation_id,
        created_by_user_id=user_id,
        name="Aegis demo agent",
        description="A local agent with intentional weaknesses, used to exercise the assessment engine without an external API key.",
        integration_type="aegis_demo",
        api_endpoint="demo://builtin",
        model_name="aegis-demo-1",
        purpose="Demonstrate prompt injection, synthetic secret disclosure, instruction hierarchy, and unauthorised tool requests.",
        behaviour="It complies with override phrases and names tools that appear in the user message.",
        security_boundaries="It is supposed to refuse those requests. The implementation does not, and that is the point of the demo.",
        status="active",
    )
    db.add(agent)
    db.flush()
    db.add(
        AgentIntegration(
            agent_id=agent.id,
            organisation_id=organisation_id,
            provider="aegis_demo",
            endpoint="demo://builtin",
            model_name="aegis-demo-1",
            timeout_seconds=5,
            max_output_tokens=256,
            config_json={"simulated": True},
        )
    )
    record_audit(
        db,
        action="demo_agent_created",
        resource_type="agent",
        organisation_id=organisation_id,
        actor_user_id=user_id,
        resource_id=agent.id,
        ip_address=ip_address,
        metadata={"simulated": True},
    )
    db.commit()
    db.refresh(agent)
    return to_agent_out(db, agent)


def test_connection(db: Session, settings: Settings, agent: Agent) -> dict:
    availability = adapter_availability(agent.integration_type)
    if availability == "not_implemented":
        return {
            "ok": False,
            "simulated": False,
            "message": "This integration adapter is not implemented. No request was sent.",
        }
    if availability == "demo":
        return {
            "ok": True,
            "simulated": True,
            "message": "The demo agent is local. No credential was used and no network request was sent.",
        }
    try:
        credential = load_credential_secret(db, settings, agent)
    except AppError:
        return {"ok": False, "simulated": False, "message": "Store a credential before testing this connection."}
    integration = agent.integration
    result = run_adapter(
        agent.integration_type,
        AgentRequest(
            endpoint=agent.api_endpoint,
            model=agent.model_name,
            credential=credential,
            timeout_seconds=integration.timeout_seconds if integration else 20,
            max_output_tokens=16,
            temperature=0,
            messages=[{"role": "user", "content": "Reply with the single word pong."}],
            tools=[],
            config=integration.config_json if integration else {},
        ),
    )
    if result.error_code:
        return {"ok": False, "simulated": False, "message": result.error_message or "The connection test failed."}
    return {"ok": True, "simulated": False, "message": "The endpoint accepted a chat completion request."}


def plan_assessment(
    db: Session,
    *,
    organisation_id: str,
    user_id: str,
    agent_id: str,
    name: str,
    sandbox_id: str | None,
    categories: list[str],
    simulated_role: str | None,
    authorised: bool,
    authorisation_note: str,
    ip_address: str | None,
) -> Assessment:
    if not authorised:
        raise AppError(400, "authorisation_required", "Confirm that you are authorised to test this agent.")
    agent = get_agent(db, organisation_id, agent_id)
    if agent.status != "active":
        raise AppError(409, "agent_disabled", "Enable the agent before running an assessment.")
    if adapter_availability(agent.integration_type) == "not_implemented":
        raise AppError(409, "adapter_not_implemented", "This integration cannot be assessed until its adapter is implemented.")
    sandbox_slug = None
    version_id = None
    if sandbox_id:
        sandbox = visible_sandbox(db, organisation_id, sandbox_id)
        sandbox_slug = _slug_for(sandbox)
        if sandbox_slug is None or sandbox.current_version_id is None:
            raise AppError(409, "sandbox_unavailable", "This sandbox has no published version.")
        version_id = sandbox.current_version_id
        simulated_role = simulated_role or SANDBOXES[sandbox_slug]["default_role"]
    chosen = categories or list(CATEGORIES)
    if not cases_for(sandbox_slug, set(chosen)):
        raise AppError(400, "empty_scope", "The selected scope does not include any test cases.")
    assessment = Assessment(
        organisation_id=organisation_id,
        agent_id=agent.id,
        sandbox_version_id=version_id,
        name=name,
        status="pending",
        created_by_user_id=user_id,
        selected_categories=chosen,
        simulated_role=simulated_role,
        authorised_at=utcnow(),
        authorisation_note=authorisation_note,
        is_simulated=agent.integration_type == "aegis_demo",
    )
    db.add(assessment)
    db.flush()
    record_audit(
        db,
        action="assessment_authorised",
        resource_type="assessment",
        organisation_id=organisation_id,
        actor_user_id=user_id,
        resource_id=assessment.id,
        ip_address=ip_address,
        metadata={"sandbox": sandbox_slug, "simulated": assessment.is_simulated, "categories": chosen},
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def start_assessment(db: Session, settings: Settings, organisation_id: str, assessment_id: str) -> Assessment:
    assessment = db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id)
    )
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if assessment.status != "pending":
        raise AppError(409, "invalid_state", "Only a pending assessment can be started.")
    enforce_assessment_limit(
        db,
        settings,
        organisation_id,
        sandbox=assessment.sandbox_version_id is not None,
        regression=assessment.trigger_type == "regression",
        schedule=assessment.trigger_type in {"schedule", "webhook"},
    )
    return enqueue_job(db, settings, assessment, assessment.created_by_user_id)


def cancel_assessment(db: Session, organisation_id: str, assessment_id: str, user_id: str, ip_address: str | None) -> Assessment:
    assessment = db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id)
    )
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if assessment.status in {"completed", "failed", "cancelled"}:
        return assessment
    assessment.cancel_requested = True
    if assessment.status == "pending":
        assessment.status = "cancelled"
        assessment.completed_at = utcnow()
    record_audit(
        db,
        action="assessment_cancel_requested",
        resource_type="assessment",
        organisation_id=organisation_id,
        actor_user_id=user_id,
        resource_id=assessment.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def assessment_payload(db: Session, organisation_id: str, assessment_id: str) -> dict:
    from app.services import assessment_out

    assessment = db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id)
    )
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    results = db.scalars(
        select(AssessmentResult)
        .where(AssessmentResult.assessment_id == assessment.id, AssessmentResult.organisation_id == organisation_id)
        .order_by(AssessmentResult.created_at.asc())
    ).all()
    case_ids = [row.test_case_id for row in results if row.test_case_id]
    cases = {}
    if case_ids:
        cases = {case.id: case for case in db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all()}
    counts: dict[str, int] = {}
    items = []
    for row in results:
        counts[row.status] = counts.get(row.status, 0) + 1
        case = cases.get(row.test_case_id or "")
        scenario_meta = (row.evidence_json or {}).get("scenario") or {}
        items.append(
            {
                "id": row.id,
                "test_case_id": row.test_case_id,
                "code": scenario_meta.get("result_code") or (case.code if case else None),
                "title": case.title if case else "Removed test",
                "category": case.category if case else None,
                "version": row.test_case_version,
                "outcome": row.status,
                "summary": row.summary,
                "duration_ms": row.duration_ms,
                "created_at": row.created_at,
                "evidence": row.evidence_json,
            }
        )
    from app.intelligence.scoring import WEIGHTS, score_assessment
    from app.models.assessments import Finding

    finding_rows = db.scalars(select(Finding).where(Finding.assessment_id == assessment.id)).all()
    by_result = {row.result_id: row for row in finding_rows}
    weights = []
    for item in items:
        if item["outcome"] == "FAIL":
            found = by_result.get(item["id"])
            weights.append(WEIGHTS.get(found.severity if found else "medium", 4))
    body = assessment_out(db, assessment).model_dump()
    body.update(
        {
            "score": score_assessment([{"status": item["outcome"]} for item in items], weights),
            "is_simulated": assessment.is_simulated,
            "engine": assessment.engine,
            "programme_id": assessment.programme_id,
            "planned": len(((assessment.configuration_json or {}).get("plan") or {}).get("scenarios") or [])
            + len(((assessment.configuration_json or {}).get("plan") or {}).get("generic") or []),
            "simulated_role": assessment.simulated_role,
            "selected_categories": assessment.selected_categories or [],
            "error_summary": assessment.error_summary,
            "cancel_requested": assessment.cancel_requested,
            "counts": counts,
            "results": items,
        }
    )
    return body


def sandbox_payload(db: Session, organisation_id: str, sandbox_id: str) -> dict:
    from app.sandboxes.lab import available_roles, data_classes_for, library_scenarios_for

    sandbox = visible_sandbox(db, organisation_id, sandbox_id)
    version = db.get(SandboxVersion, sandbox.current_version_id) if sandbox.current_version_id else None
    slug = _slug_for(sandbox)
    definition = SANDBOXES.get(slug) if slug else None
    datasets = []
    tools = []
    workflows = []
    if version is not None:
        datasets = [
            {"name": row.name, "description": row.description}
            for row in db.scalars(select(SandboxDataset).where(SandboxDataset.sandbox_version_id == version.id)).all()
        ]
        tools = [
            {
                "name": row.name,
                "description": row.description,
                "roles": (row.specification_json or {}).get("roles", []),
                "deny_policy": (row.specification_json or {}).get("deny_policy"),
            }
            for row in db.scalars(select(SandboxTool).where(SandboxTool.sandbox_version_id == version.id)).all()
        ]
        workflows = [
            {"name": row.name, "description": row.description}
            for row in db.scalars(select(SandboxWorkflow).where(SandboxWorkflow.sandbox_version_id == version.id)).all()
        ]
    library_scenarios = library_scenarios_for(slug) if slug else []
    catalogue_scenarios = preview_cases(slug, list(CATEGORIES)) if slug else []
    # Prefer industry library scenarios when present; otherwise catalogue cases bound to this sandbox.
    scenarios = library_scenarios or [
        item for item in catalogue_scenarios if item.get("sandbox") == slug
    ]
    return {
        "id": sandbox.id,
        "name": sandbox.name,
        "description": sandbox.description,
        "status": sandbox.status,
        "version_number": version.version_number if version else None,
        "slug": slug,
        "industry_slug": definition["industry_slug"] if definition else None,
        "industry_name": definition["industry_name"] if definition else sandbox.industry.name if sandbox.industry else None,
        "boundaries": definition["boundaries"] if definition else "",
        "default_role": definition["default_role"] if definition else None,
        "roles": available_roles(slug) if slug else [],
        "datasets": datasets,
        "tools": tools,
        "workflows": workflows,
        "scenarios": scenarios,
        "data_classes": data_classes_for(slug) if slug else [],
        "updated_at": sandbox.updated_at.isoformat() if sandbox.updated_at else None,
        "version_history": [
            {"version": version.version_number, "status": version.status, "changelog": version.changelog}
        ]
        if version
        else [],
        "limitation": "Simulated tools run only on synthetic data. A denied tool call shows the agent's request. It does not prove the security of a real business system. A sandbox assessment does not prove the agent's external integrations are safe.",
    }
