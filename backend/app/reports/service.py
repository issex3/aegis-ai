"""Generate and authorise assessment PDFs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.operations import assessment_payload
from app.errors import AppError
from app.models.agents import Agent
from app.models.assessments import Assessment, AssessmentComparison, Finding, Remediation, Report
from app.models.identity import Organisation
from app.models.sandboxes import Sandbox, SandboxVersion
from app.reports.pdf import build_assessment_pdf
from app.services import record_audit

PLANNED_INDUSTRIES = [
    {"name": "Insurance", "status": "not_available", "description": "Claims and policy-servicing workflows. Not implemented."},
    {"name": "Recruitment", "status": "not_available", "description": "Candidate and hiring workflows. Not implemented."},
    {"name": "Property", "status": "not_available", "description": "Lettings and property-management workflows. Not implemented."},
    {"name": "Education", "status": "not_available", "description": "Student-record and teaching workflows. Not implemented."},
    {"name": "Financial services", "status": "not_available", "description": "Broader than the accounting sandbox. Not implemented as its own environment."},
    {"name": "Logistics", "status": "not_available", "description": "Shipment and warehouse workflows. Not implemented."},
]


def _owned_report(db: Session, organisation_id: str, report_id: str) -> Report:
    report = db.scalar(select(Report).where(Report.id == report_id, Report.organisation_id == organisation_id))
    if report is None:
        raise AppError(404, "not_found", "Report not found.")
    return report


def _context(db: Session, organisation_id: str, assessment_id: str) -> dict:
    detail = assessment_payload(db, organisation_id, assessment_id)
    if detail["status"] != "completed":
        raise AppError(409, "invalid_state", "Generate a report after the assessment has completed.")
    assessment = db.get(Assessment, assessment_id)
    agent = db.get(Agent, assessment.agent_id)
    organisation = db.get(Organisation, organisation_id)
    sandbox_name = None
    sandbox_version = None
    if assessment.sandbox_version_id:
        version = db.get(SandboxVersion, assessment.sandbox_version_id)
        sandbox = db.get(Sandbox, version.sandbox_id) if version else None
        sandbox_name = sandbox.name if sandbox else None
        sandbox_version = version.version_number if version else None
    findings = db.scalars(select(Finding).where(Finding.assessment_id == assessment.id, Finding.organisation_id == organisation_id)).all()
    rendered = []
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
        remediation = db.scalar(select(Remediation).where(Remediation.finding_id == finding.id))
        evidence = db.scalars(select(Finding).where(Finding.id == finding.id)).first()
        from app.models.assessments import FindingEvidence

        pieces = db.scalars(select(FindingEvidence).where(FindingEvidence.finding_id == finding.id)).all()
        rendered.append(
            {
                "title": finding.title,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "description": finding.description,
                "business_impact": finding.business_impact,
                "expected_behaviour": finding.expected_behaviour,
                "actual_behaviour": finding.actual_behaviour,
                "reproduction_steps": finding.reproduction_steps,
                "evidence": " ".join(piece.content[:500] for piece in pieces) or "No separate evidence row was stored.",
                "remediation": remediation.guidance if remediation else "See the remediation catalogue for this category.",
                "severity_rule": finding.severity_rule or "unspecified",
                "simulated": bool(assessment.is_simulated),
            }
        )
        _ = evidence
    comparison = db.scalar(
        select(AssessmentComparison)
        .where(
            (AssessmentComparison.baseline_assessment_id == assessment.id) | (AssessmentComparison.compared_assessment_id == assessment.id),
            AssessmentComparison.organisation_id == organisation_id,
        )
        .order_by(AssessmentComparison.created_at.desc())
    )
    score = detail.get("score") or {}
    limitations = [
        "Only the observable reply and tool calls were judged.",
        "Sandbox tools changed fictional records in memory.",
        "Inconclusive and errored tests were not scored as passes or failures.",
        "A sandbox result does not prove the agent's real external systems are safe.",
    ]
    if assessment.is_simulated:
        limitations.insert(0, "This assessment used the built-in demo agent. The weaknesses are simulated.")
    return {
        "organisation_name": organisation.name,
        "agent_name": agent.name,
        "agent_description": agent.description,
        "assessment_name": assessment.name,
        "assessment_id": assessment.id,
        "assessment_date": (assessment.completed_at or assessment.created_at).isoformat(),
        "integration_type": agent.integration_type,
        "model_name": agent.model_name,
        "sandbox_name": sandbox_name,
        "sandbox_version": sandbox_version,
        "scope": ", ".join(assessment.selected_categories or []) or "All categories in the selected suite",
        "executive_summary": (
            f"{score.get('failed', 0)} applicable failures and {score.get('passed', 0)} passes were observed. "
            f"Classification: {score.get('classification', 'not scored')}."
        ),
        "score_text": "Not scored" if score.get("score") is None else str(score.get("score")),
        "classification": score.get("classification", "not scored"),
        "coverage": f"{round((score.get('coverage') or 0) * 100)}%",
        "applicable": score.get("applicable_tests", 0),
        "inconclusive": score.get("inconclusive", 0),
        "errors": score.get("errors", 0),
        "skipped": score.get("skipped", 0),
        "score_disclaimer": score.get("disclaimer", "Internal assessment metric. Not a certification."),
        "severity_counts": counts,
        "findings": rendered,
        "regression": comparison.summary if comparison else "",
        "limitations": limitations,
    }


def generate_report(db: Session, organisation_id: str, user_id: str, assessment_id: str, ip_address: str | None, regenerate_id: str | None = None) -> Report:
    context = _context(db, organisation_id, assessment_id)
    pdf = build_assessment_pdf(context)
    title = f"{context['agent_name']} — {context['assessment_name']}"
    if regenerate_id:
        report = _owned_report(db, organisation_id, regenerate_id)
        report.document = pdf
        report.byte_size = len(pdf)
        report.summary = context["executive_summary"]
        report.status = "ready"
        action = "report_regenerated"
    else:
        report = Report(
            organisation_id=organisation_id,
            assessment_id=assessment_id,
            title=title[:200],
            status="ready",
            summary=context["executive_summary"],
            document=pdf,
            byte_size=len(pdf),
            created_by_user_id=user_id,
        )
        db.add(report)
        action = "report_generated"
    db.flush()
    record_audit(db, action=action, resource_type="report", organisation_id=organisation_id, actor_user_id=user_id, resource_id=report.id, ip_address=ip_address, metadata={"assessment_id": assessment_id, "bytes": len(pdf)})
    db.commit()
    db.refresh(report)
    return report


def read_report(db: Session, organisation_id: str, user_id: str, report_id: str, ip_address: str | None) -> tuple[str, bytes]:
    report = _owned_report(db, organisation_id, report_id)
    if not report.document:
        raise AppError(404, "not_found", "Report not found.")
    record_audit(db, action="report_downloaded", resource_type="report", organisation_id=organisation_id, actor_user_id=user_id, resource_id=report.id, ip_address=ip_address)
    db.commit()
    return report.id, bytes(report.document)


def catalogue(db: Session, organisation_id: str) -> dict:
    from app.engine.operations import sandbox_payload
    from app.services import list_visible_sandboxes

    available = []
    for summary in list_visible_sandboxes(db, organisation_id):
        detail = sandbox_payload(db, organisation_id, summary.id)
        scenarios = detail["scenarios"]
        available.append(
            {
                **summary.model_dump(),
                "availability": "available",
                "slug": detail.get("slug"),
                "industry_slug": detail.get("industry_slug"),
                "scenario_count": len(scenarios),
                "categories": sorted({item["category"] for item in scenarios}),
                "tools": [tool["name"] for tool in detail["tools"]],
                "workflows": [item["name"] for item in detail["workflows"]],
                "datasets": [item["name"] for item in detail["datasets"]],
                "roles": detail.get("roles") or [],
                "data_classes": detail.get("data_classes") or [],
                "default_role": detail.get("default_role"),
                "boundaries": detail.get("boundaries") or "",
                "updated_at": detail.get("updated_at"),
                "limitation": detail["limitation"],
            }
        )
    return {"available": available, "planned": PLANNED_INDUSTRIES}


def delete_report(db: Session, organisation_id: str, user_id: str, report_id: str, ip_address: str | None) -> None:
    report = _owned_report(db, organisation_id, report_id)
    record_audit(db, action="report_deleted", resource_type="report", organisation_id=organisation_id, actor_user_id=user_id, resource_id=report.id, ip_address=ip_address)
    db.delete(report)
    db.commit()


def onboarding_state(db: Session, organisation_id: str) -> dict:
    from app.models.agents import Agent, AgentCredential

    agents = db.scalars(select(Agent).where(Agent.organisation_id == organisation_id, Agent.deleted_at.is_(None))).all()
    assessments = db.scalars(select(Assessment).where(Assessment.organisation_id == organisation_id)).all()
    connected = False
    for agent in agents:
        if agent.integration_type == "aegis_demo":
            connected = True
        elif db.scalar(select(AgentCredential).where(AgentCredential.agent_id == agent.id, AgentCredential.deleted_at.is_(None))):
            connected = True
    completed = [item for item in assessments if item.status == "completed"]
    steps = [
        {"id": "organisation", "label": "Create an organisation", "done": True},
        {"id": "agent", "label": "Add an agent", "done": bool(agents)},
        {"id": "integration", "label": "Choose an integration", "done": bool(agents)},
        {"id": "connection", "label": "Confirm the agent can be called", "done": connected},
        {"id": "industry", "label": "Choose an industry sandbox", "done": any(item.sandbox_version_id for item in assessments)},
        {"id": "assessment", "label": "Run an assessment", "done": bool(completed)},
        {"id": "results", "label": "Review findings", "done": bool(completed)},
    ]
    return {"steps": steps, "complete": all(step["done"] for step in steps)}
