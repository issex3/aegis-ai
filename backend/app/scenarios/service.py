"""Profiles, testing programmes, launch, and intelligence reporting."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.engine.catalog import CATEGORIES, cases_for
from app.errors import AppError
from app.integrations.registry import adapter_availability
from app.intelligence.regression import compare_results
from app.intelligence.scoring import WEIGHTS, score_assessment
from app.models.agents import Agent
from app.models.assessments import Assessment, AssessmentResult, Finding, TestCase
from app.models.base import utcnow
from app.models.sandboxes import Sandbox
from app.sandboxes.definitions import SANDBOXES
from app.scenarios import registry
from app.scenarios.models import AgentProfile, AssessmentLog, TestingProgramme
from app.scenarios.profiling import analyse
from app.scenarios.selection import INTENSITIES, build_selection, default_selection
from app.scenarios.taxonomy import BASELINE_CAPABILITIES, CAPABILITIES, DATA_CLASSES, INDUSTRIES, THREATS
from app.services import get_agent, record_audit

PROFILE_FIELDS = ("description", "purpose", "responsibilities", "tools", "permissions", "data_types", "authorised_actions")


def _profile_dict(profile: AgentProfile) -> dict:
    return {
        "industry": profile.industry,
        "description": profile.description,
        "purpose": profile.purpose,
        "responsibilities": profile.responsibilities,
        "tools": profile.tools,
        "permissions": profile.permissions,
        "data_types": profile.data_types,
        "authorised_actions": profile.authorised_actions,
        "risk_sensitivity": profile.risk_sensitivity,
    }


def profile_out(profile: AgentProfile) -> dict:
    return {
        "id": profile.id,
        "agent_id": profile.agent_id,
        **_profile_dict(profile),
        "capabilities": profile.capabilities,
        "analysis": profile.analysis_json,
        "version": profile.version,
        "updated_at": profile.updated_at,
    }


def get_profile(db: Session, organisation_id: str, agent_id: str) -> AgentProfile | None:
    get_agent(db, organisation_id, agent_id)
    return db.scalar(select(AgentProfile).where(AgentProfile.agent_id == agent_id, AgentProfile.organisation_id == organisation_id))


def save_profile(db: Session, organisation_id: str, user_id: str, agent_id: str, payload: dict, ip_address: str | None) -> AgentProfile:
    agent = get_agent(db, organisation_id, agent_id)
    if payload["industry"] not in INDUSTRIES:
        raise AppError(400, "unknown_industry", "Choose a supported industry.")
    analysis = analyse(payload)
    inferred = [item["key"] for item in analysis["capabilities"]]
    confirmed = payload.get("capabilities")
    capabilities = list(dict.fromkeys([*(confirmed if confirmed is not None else inferred), *BASELINE_CAPABILITIES]))
    profile = db.scalar(select(AgentProfile).where(AgentProfile.agent_id == agent.id))
    values = {key: payload.get(key) for key in (*PROFILE_FIELDS, "industry", "risk_sensitivity")}
    if profile is None:
        profile = AgentProfile(organisation_id=organisation_id, agent_id=agent.id, version=1, **values)
        db.add(profile)
    else:
        changed = _profile_dict(profile) != values or profile.capabilities != capabilities
        for key, value in values.items():
            setattr(profile, key, value)
        if changed:
            profile.version += 1
    profile.capabilities = capabilities
    profile.analysis_json = analysis
    profile.updated_by_user_id = user_id
    db.flush()
    record_audit(db, action="agent_profile_saved", resource_type="agent", organisation_id=organisation_id, actor_user_id=user_id, resource_id=agent.id, ip_address=ip_address, metadata={"industry": profile.industry, "version": profile.version, "capabilities": len(capabilities)})
    db.commit()
    db.refresh(profile)
    return profile


def _data_classes(profile: AgentProfile) -> list[str]:
    return [item["key"] for item in (profile.analysis_json or {}).get("data_classes", [])]


def _programme_stats(programme: TestingProgramme) -> dict:
    entries = programme.selection_json or []
    applicable = [entry for entry in entries if entry["applicable"]]
    selected = [entry for entry in entries if entry["selected"]]
    executions = sum(1 + (entry["variants"] if programme.intensity == "extended" else 0) for entry in selected)
    generic = len(cases_for(None, set(programme.generic_categories) or None)) if programme.include_generic else 0
    threats = {}
    for key, meta in THREATS.items():
        relevant = [entry for entry in applicable if entry["threat"] == key]
        chosen = [entry for entry in selected if entry["threat"] == key]
        if relevant or chosen:
            threats[key] = {"name": meta["name"], "applicable": len(relevant), "selected": len(chosen)}
    by_priority = {band: sum(1 for entry in selected if entry["priority"] == band) for band in ("P1", "P2", "P3")}
    return {
        "library": len(entries),
        "applicable": len(applicable),
        "not_applicable": len(entries) - len(applicable),
        "selected": len(selected),
        "overrides": sum(1 for entry in selected if entry["override"]),
        "executions": executions,
        "generic": generic,
        "threats": threats,
        "by_priority": by_priority,
    }


def programme_out(db: Session, programme: TestingProgramme) -> dict:
    agent = db.get(Agent, programme.agent_id)
    runs = db.scalars(
        select(Assessment).where(Assessment.programme_id == programme.id).order_by(Assessment.created_at.desc())
    ).all()
    return {
        "id": programme.id,
        "agent_id": programme.agent_id,
        "agent_name": agent.name if agent else "Removed agent",
        "agent_simulated": bool(agent and agent.integration_type == "aegis_demo"),
        "industry": programme.industry,
        "industry_name": INDUSTRIES[programme.industry].name if programme.industry in INDUSTRIES else programme.industry,
        "profile_version": programme.profile_version,
        "intensity": programme.intensity,
        "intensities": INTENSITIES,
        "include_generic": programme.include_generic,
        "generic_categories": programme.generic_categories,
        "status": programme.status,
        "selection": programme.selection_json,
        "profile": programme.profile_snapshot,
        "stats": _programme_stats(programme),
        "runs": [{"id": run.id, "name": run.name, "status": run.status, "created_at": run.created_at} for run in runs],
        "created_at": programme.created_at,
        "updated_at": programme.updated_at,
    }


def get_programme(db: Session, organisation_id: str, programme_id: str) -> TestingProgramme:
    programme = db.scalar(select(TestingProgramme).where(TestingProgramme.id == programme_id, TestingProgramme.organisation_id == organisation_id))
    if programme is None:
        raise AppError(404, "not_found", "Programme not found.")
    return programme


def list_programmes(db: Session, organisation_id: str) -> list[dict]:
    rows = db.scalars(select(TestingProgramme).where(TestingProgramme.organisation_id == organisation_id).order_by(TestingProgramme.created_at.desc())).all()
    return [programme_out(db, row) for row in rows]


def create_programme(db: Session, organisation_id: str, user_id: str, agent_id: str, intensity: str, include_generic: bool, ip_address: str | None) -> TestingProgramme:
    agent = get_agent(db, organisation_id, agent_id)
    profile = db.scalar(select(AgentProfile).where(AgentProfile.agent_id == agent.id))
    if profile is None:
        raise AppError(409, "profile_required", "Profile the agent before building a programme.")
    data_classes = _data_classes(profile)
    programme = TestingProgramme(
        organisation_id=organisation_id,
        agent_id=agent.id,
        industry=profile.industry,
        profile_version=profile.version,
        intensity=intensity,
        include_generic=include_generic,
        generic_categories=[],
        selection_json=build_selection(profile.industry, profile.capabilities, data_classes, profile.risk_sensitivity, intensity),
        profile_snapshot={
            "industry": profile.industry,
            "version": profile.version,
            "capabilities": [{"key": key, "label": CAPABILITIES[key].label} for key in profile.capabilities if key in CAPABILITIES],
            "data_classes": [{"key": key, "label": DATA_CLASSES[key]} for key in data_classes],
            "risk_sensitivity": profile.risk_sensitivity,
            "purpose": profile.purpose,
        },
        status="draft",
        created_by_user_id=user_id,
    )
    db.add(programme)
    db.flush()
    record_audit(db, action="programme_created", resource_type="testing_programme", organisation_id=organisation_id, actor_user_id=user_id, resource_id=programme.id, ip_address=ip_address, metadata={"agent_id": agent.id, "industry": profile.industry})
    db.commit()
    db.refresh(programme)
    return programme


def update_programme(db: Session, organisation_id: str, programme_id: str, payload: dict) -> TestingProgramme:
    programme = get_programme(db, organisation_id, programme_id)
    entries = [dict(entry) for entry in programme.selection_json or []]
    known = {entry["code"] for entry in entries}
    if payload.get("intensity") is not None:
        programme.intensity = payload["intensity"]
        if payload.get("selected") is None:
            entries = default_selection(entries, programme.intensity)
    if payload.get("selected") is not None:
        chosen = set(payload["selected"])
        unknown = chosen - known
        if unknown:
            raise AppError(400, "unknown_scenario", "One or more scenarios are not part of this programme.")
        for entry in entries:
            entry["selected"] = entry["code"] in chosen
            entry["override"] = entry["selected"] and not entry["applicable"]
    if payload.get("include_generic") is not None:
        programme.include_generic = payload["include_generic"]
    if payload.get("generic_categories") is not None:
        invalid = [item for item in payload["generic_categories"] if item not in CATEGORIES]
        if invalid:
            raise AppError(400, "unknown_category", "One or more generic categories are not supported.")
        programme.generic_categories = list(dict.fromkeys(payload["generic_categories"]))
    programme.selection_json = entries
    db.commit()
    db.refresh(programme)
    return programme


def _sandbox_version_id(db: Session, slug: str) -> str | None:
    sandbox = db.scalar(select(Sandbox).where(Sandbox.name == SANDBOXES[slug]["name"], Sandbox.organisation_id.is_(None)))
    return sandbox.current_version_id if sandbox else None


def launch_programme(
    db: Session,
    settings: Settings,
    *,
    organisation_id: str,
    user_id: str,
    programme_id: str,
    name: str,
    authorised: bool,
    authorisation_note: str,
    ip_address: str | None,
    trigger_type: str = "manual",
    parent_assessment_id: str | None = None,
) -> Assessment:
    from app.engine.operations import start_assessment

    if not authorised:
        raise AppError(400, "authorisation_required", "Confirm that you are authorised to test this agent.")
    programme = get_programme(db, organisation_id, programme_id)
    agent = get_agent(db, organisation_id, programme.agent_id)
    if agent.status != "active":
        raise AppError(409, "agent_disabled", "Enable the agent before running a programme.")
    if adapter_availability(agent.integration_type) == "not_implemented":
        raise AppError(409, "adapter_not_implemented", "This integration cannot be assessed until its adapter is implemented.")
    selected = [entry for entry in programme.selection_json or [] if entry["selected"]]
    plan_items = []
    for entry in selected:
        scenario = registry.get(entry["code"])
        if scenario is None:
            continue
        variants = len(scenario.variants) if programme.intensity == "extended" else 0
        for variant in range(variants + 1):
            plan_items.append({"code": scenario.code, "version": scenario.version, "content_hash": scenario.content_hash(), "variant": variant, "priority": entry["priority"]})
    generic = [case.code for case in cases_for(None, set(programme.generic_categories) or None)] if programme.include_generic else []
    if not plan_items and not generic:
        raise AppError(400, "empty_scope", "Select at least one scenario or include generic checks.")
    industry = INDUSTRIES[programme.industry]
    sandbox = SANDBOXES[industry.sandbox]
    import hashlib

    assessment = Assessment(
        organisation_id=organisation_id,
        agent_id=agent.id,
        sandbox_version_id=_sandbox_version_id(db, industry.sandbox),
        name=name,
        status="pending",
        created_by_user_id=user_id,
        selected_categories=sorted({registry.get(item["code"]).category for item in plan_items}),
        simulated_role=sandbox["default_role"],
        authorised_at=utcnow(),
        authorisation_note=authorisation_note,
        is_simulated=agent.integration_type == "aegis_demo",
        engine="scenario",
        programme_id=programme.id,
        trigger_type=trigger_type,
        parent_assessment_id=parent_assessment_id,
        configuration_json={
            "plan": {"scenarios": plan_items, "generic": generic},
            "programme_id": programme.id,
            "industry": programme.industry,
            "intensity": programme.intensity,
            "profile_version": programme.profile_version,
            "profile": programme.profile_snapshot,
            "integration_type": agent.integration_type,
            "model_name": agent.model_name,
            "weakness_profile": ((agent.integration.config_json or {}).get("weakness_profile", "default") if agent.integration else "default"),
            "boundary_fingerprint": hashlib.sha256(agent.security_boundaries.encode("utf-8")).hexdigest(),
            "trigger": trigger_type,
        },
    )
    db.add(assessment)
    programme.status = "launched"
    db.flush()
    record_audit(db, action="programme_launched", resource_type="assessment", organisation_id=organisation_id, actor_user_id=user_id, resource_id=assessment.id, ip_address=ip_address, metadata={"programme_id": programme.id, "scenarios": len(plan_items), "generic": len(generic), "simulated": assessment.is_simulated})
    db.commit()
    db.refresh(assessment)
    return start_assessment(db, settings, organisation_id, assessment.id)


def assessment_logs(db: Session, organisation_id: str, assessment_id: str, after: int = 0) -> list[dict]:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    rows = db.scalars(
        select(AssessmentLog)
        .where(AssessmentLog.assessment_id == assessment.id, AssessmentLog.sequence > after)
        .order_by(AssessmentLog.sequence.asc())
        .limit(500)
    ).all()
    return [{"sequence": row.sequence, "level": row.level, "event": row.event, "message": row.message, "data": row.data_json, "created_at": row.created_at} for row in rows]


def _scored(rows: list[dict]) -> dict:
    weights = [WEIGHTS.get(row["severity"] or "medium", 4) for row in rows if row["outcome"] == "FAIL"]
    return score_assessment([{"status": row["outcome"]} for row in rows], weights)


def _result_rows(db: Session, assessment: Assessment) -> list[dict]:
    results = db.scalars(select(AssessmentResult).where(AssessmentResult.assessment_id == assessment.id).order_by(AssessmentResult.created_at.asc())).all()
    findings = {row.result_id: row for row in db.scalars(select(Finding).where(Finding.assessment_id == assessment.id)).all()}
    case_ids = {row.test_case_id for row in results if row.test_case_id}
    cases = {case.id: case for case in db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all()} if case_ids else {}
    rows = []
    for result in results:
        evidence = result.evidence_json or {}
        meta = evidence.get("scenario") or {}
        case = cases.get(result.test_case_id or "")
        finding = findings.get(result.id)
        scenario = registry.get(meta.get("code", "")) if meta else None
        rows.append(
            {
                "id": result.id,
                "code": meta.get("result_code") or (case.code if case else None),
                "scenario_code": meta.get("code"),
                "kind": "scenario" if meta else "generic",
                "title": (scenario.name + (f" (variant {meta.get('variant')})" if meta.get("variant") else "")) if scenario else (case.title if case else "Removed test"),
                "threat": scenario.threat if scenario else None,
                "category": scenario.category if scenario else (case.category if case else None),
                "risk": scenario.risk if scenario else (case.severity if case else None),
                "outcome": result.status,
                "severity": finding.severity if finding else None,
                "finding_id": finding.id if finding else None,
                "summary": result.summary,
                "variant": meta.get("variant", 0),
            }
        )
    return rows


def _tally(rows: list[dict], key: str, labels: dict | None = None) -> list[dict]:
    groups: dict[str, dict] = {}
    for row in rows:
        group = row.get(key) or "unclassified"
        bucket = groups.setdefault(group, {"key": group, "label": (labels or {}).get(group, group), "PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "ERROR": 0, "SKIPPED": 0})
        bucket[row["outcome"]] = bucket.get(row["outcome"], 0) + 1
    return sorted(groups.values(), key=lambda item: (-item["FAIL"], item["key"]))


def programme_report(db: Session, organisation_id: str, assessment_id: str) -> dict:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    if assessment.engine != "scenario":
        raise AppError(409, "not_a_programme", "This assessment was not run from a testing programme.")
    config = assessment.configuration_json or {}
    rows = _result_rows(db, assessment)
    scenario_rows = [row for row in rows if row["kind"] == "scenario"]
    generic_rows = [row for row in rows if row["kind"] == "generic"]
    industry = config.get("industry")
    plan = config.get("plan") or {}
    planned = len(plan.get("scenarios") or []) + len(plan.get("generic") or [])
    executed = [row for row in rows if row["outcome"] in {"PASS", "FAIL"}]
    library = registry.for_industry(industry) if industry else []
    tested_threats = {row["threat"] for row in scenario_rows if row["outcome"] in {"PASS", "FAIL"} and row["threat"]}
    library_threats = {scenario.threat for scenario in library}
    critical = [
        {"code": row["code"], "title": row["title"], "summary": row["summary"], "finding_id": row["finding_id"], "threat": row["threat"]}
        for row in rows
        if row["outcome"] == "FAIL" and row["severity"] == "critical"
    ]
    remediation: list[dict] = []
    seen: set[str] = set()
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    for row in sorted((row for row in scenario_rows if row["outcome"] == "FAIL"), key=lambda item: order.get(item["severity"] or "medium", 2)):
        scenario = registry.get(row["scenario_code"] or "")
        if scenario is None:
            continue
        for step in scenario.remediation:
            if step not in seen:
                seen.add(step)
                remediation.append({"step": step, "severity": row["severity"], "source": row["code"]})

    comparison = None
    previous = db.scalar(
        select(Assessment)
        .where(
            Assessment.organisation_id == organisation_id,
            Assessment.agent_id == assessment.agent_id,
            Assessment.engine == "scenario",
            Assessment.status == "completed",
            Assessment.created_at < assessment.created_at,
            Assessment.id != assessment.id,
        )
        .order_by(Assessment.created_at.desc())
    )
    if previous is not None and assessment.status == "completed":
        previous_rows = _result_rows(db, previous)
        diff = compare_results(previous_rows, rows)
        previous_score = _scored(previous_rows)["score"]
        current_score = _scored(rows)["score"]
        comparison = {
            "previous_id": previous.id,
            "previous_name": previous.name,
            "previous_score": previous_score,
            "score_delta": None if previous_score is None or current_score is None else current_score - previous_score,
            "counts": diff["counts"],
            "changes": [item for item in diff["items"] if item["status"] in {"new_vulnerability", "resolved_vulnerability", "persistent_vulnerability"}],
        }

    return {
        "assessment_id": assessment.id,
        "status": assessment.status,
        "is_simulated": assessment.is_simulated,
        "industry": industry,
        "industry_name": INDUSTRIES[industry].name if industry in INDUSTRIES else industry,
        "intensity": config.get("intensity"),
        "profile": config.get("profile"),
        "overall_score": _scored(rows),
        "industry_score": _scored(scenario_rows),
        "generic_score": _scored(generic_rows) if generic_rows else None,
        "outcomes": {status: sum(1 for row in rows if row["outcome"] == status) for status in ("PASS", "FAIL", "INCONCLUSIVE", "ERROR", "SKIPPED")},
        "by_threat": _tally(scenario_rows, "threat", {key: meta["name"] for key, meta in THREATS.items()}),
        "by_risk": _tally(scenario_rows, "risk"),
        "critical": critical,
        "remediation": remediation[:12],
        "coverage": {
            "planned": planned,
            "recorded": len(rows),
            "executed": len(executed),
            "inconclusive": sum(1 for row in rows if row["outcome"] == "INCONCLUSIVE"),
            "could_not_execute": sum(1 for row in rows if row["outcome"] in {"ERROR", "SKIPPED"}),
            "library_size": len(library),
            "threats_tested": sorted(tested_threats),
            "threats_in_library": sorted(library_threats),
        },
        "rows": rows,
        "comparison": comparison,
        "definitions": {
            "FAIL": "The agent's observed behaviour matched a failure condition.",
            "INCONCLUSIVE": "The run completed, but the evidence could not show a pass or a failure.",
            "ERROR": "The scenario could not execute, for example a timeout or an unreachable endpoint.",
            "SKIPPED": "The scenario did not run because the assessment was cancelled.",
        },
        "disclaimer": "Internal assessment metric. Not a certification or a guarantee of security. Scenarios run against synthetic sandboxes.",
    }
