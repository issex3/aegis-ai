"""Persist the platform catalogue. Safe to run more than once."""

import hashlib
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.catalog import CASES
from app.models.assessments import AssessmentSuite, TestCase
from app.models.base import new_id, utcnow
from app.models.sandboxes import Industry, Sandbox, SandboxDataset, SandboxTool, SandboxVersion, SandboxWorkflow
from app.sandboxes.definitions import SANDBOXES

logger = logging.getLogger("aegis")


def _tags(case) -> list[str]:
    tags = list(case.tags)
    tags.extend(f"marker:{marker}" for marker in case.markers)
    tags.extend(f"tool:{name}" for name in case.forbidden_tools)
    return tags


def sandbox_fingerprint(definition: dict) -> str:
    body = {
        "datasets": definition["datasets"],
        "workflows": definition["workflows"],
        "boundaries": definition["boundaries"],
        "tools": sorted(
            (spec["name"], sorted(spec["roles"]), spec["deny_policy"], spec["allow_policy"], sorted(spec.get("params", {})))
            for spec in definition["tools"].values()
        ),
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=list).encode("utf-8")).hexdigest()


def _publish_version(db: Session, sandbox: Sandbox, definition: dict, number: int, changelog: str, fingerprint: str) -> SandboxVersion:
    version = SandboxVersion(sandbox_id=sandbox.id, version_number=number, status="published", changelog=changelog, fingerprint=fingerprint)
    db.add(version)
    db.flush()
    for name, description in definition["datasets"]:
        db.add(SandboxDataset(sandbox_version_id=version.id, name=name, description=description, schema_json={"synthetic": True}))
    for spec in definition["tools"].values():
        db.add(
            SandboxTool(
                sandbox_version_id=version.id,
                name=spec["name"],
                description=spec["description"],
                specification_json={
                    "roles": sorted(spec["roles"]),
                    "deny_policy": spec["deny_policy"],
                    "allow_policy": spec["allow_policy"],
                    "params": spec.get("params", {}),
                },
            )
        )
    for name, description in definition["workflows"]:
        db.add(SandboxWorkflow(sandbox_version_id=version.id, name=name, description=description, definition_json={"boundaries": definition["boundaries"]}))
    sandbox.current_version_id = version.id
    sandbox.description = definition["description"]
    return version


def _ensure_sandbox(db: Session, industry: Industry, definition: dict) -> None:
    fingerprint = sandbox_fingerprint(definition)
    sandbox = db.scalar(select(Sandbox).where(Sandbox.name == definition["name"], Sandbox.organisation_id.is_(None)))
    if sandbox is None:
        sandbox = Sandbox(organisation_id=None, industry_id=industry.id, name=definition["name"], description=definition["description"], status="published")
        db.add(sandbox)
        db.flush()
        _publish_version(db, sandbox, definition, 1, "Initial synthetic environment.", fingerprint)
        return
    current = db.get(SandboxVersion, sandbox.current_version_id) if sandbox.current_version_id else None
    if current is not None and current.fingerprint == fingerprint:
        return
    existing_tools = {row.name for row in db.scalars(select(SandboxTool).where(SandboxTool.sandbox_version_id == current.id)).all()} if current else set()
    defined_tools = set(definition["tools"])
    if current is not None and current.fingerprint is None and existing_tools == defined_tools:
        current.fingerprint = fingerprint
        return
    added = sorted(defined_tools - existing_tools)
    removed = sorted(existing_tools - defined_tools)
    notes = []
    if added:
        notes.append("Added tools: " + ", ".join(added) + ".")
    if removed:
        notes.append("Removed tools: " + ", ".join(removed) + ".")
    notes.append("Updated synthetic records and workflows.")
    number = (current.version_number if current else 0) + 1
    _publish_version(db, sandbox, definition, number, " ".join(notes), fingerprint)


def ensure_platform_content(db: Session) -> None:
    industries: dict[str, Industry] = {}
    for slug, definition in SANDBOXES.items():
        industry = db.scalar(select(Industry).where(Industry.slug == definition["industry_slug"]))
        if industry is None:
            industry = Industry(
                id=new_id(),
                slug=definition["industry_slug"],
                name=definition["industry_name"],
                description=definition["industry_description"],
                created_at=utcnow(),
            )
            db.add(industry)
            db.flush()
        industries[slug] = industry
        _ensure_sandbox(db, industry, definition)

    suite_by_slug: dict[str | None, AssessmentSuite] = {}
    for key, name, description, industry in (
        (None, "Generic agent controls", "Text-only checks that do not depend on an industry tool model.", None),
        ("accounting", "Accounting sandbox suite", "Checks that use the accounting sandbox tools and records.", industries["accounting"].id),
        ("legal", "Legal sandbox suite", "Checks that use the legal sandbox tools and records.", industries["legal"].id),
        ("retail", "Retail sandbox suite", "Checks that use the retail sandbox tools and records.", industries["retail"].id),
    ):
        suite = db.scalar(select(AssessmentSuite).where(AssessmentSuite.name == name, AssessmentSuite.organisation_id.is_(None)))
        if suite is None:
            suite = AssessmentSuite(organisation_id=None, industry_id=industry, name=name, description=description)
            db.add(suite)
            db.flush()
        suite_by_slug[key] = suite

    for spec in CASES:
        existing = db.scalar(select(TestCase).where(TestCase.code == spec.code))
        payload = dict(
            suite_id=suite_by_slug[spec.sandbox].id,
            title=spec.title,
            description=spec.description,
            objective=spec.expected_behaviour,
            severity=spec.severity,
            procedure=spec.attack_scenario,
            is_platform=True,
            category=spec.category,
            attack_scenario=spec.attack_scenario,
            test_input=spec.test_input,
            expected_behaviour=spec.expected_behaviour,
            evaluation_criteria=spec.evaluation_criteria,
            evidence_requirements=spec.evidence_requirements,
            remediation_guidance=spec.remediation_guidance,
            version=spec.version,
            tags=_tags(spec),
            requires_tools=spec.requires_tools,
        )
        if existing is None:
            case = TestCase(organisation_id=None, code=spec.code, **payload)
            if spec.sandbox is not None:
                case.industries = [industries[spec.sandbox]]
            db.add(case)
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
            if spec.sandbox is not None:
                existing.industries = [industries[spec.sandbox]]
    db.flush()
    ensure_scenario_library(db, industries)
    db.commit()


def ensure_scenario_library(db: Session, industries: dict[str, Industry]) -> None:
    from app.scenarios.registry import SCENARIOS
    from app.scenarios.taxonomy import INDUSTRIES

    suites: dict[str, AssessmentSuite] = {}
    for slug, industry_definition in INDUSTRIES.items():
        name = f"Scenario library: {industry_definition.name}"
        suite = db.scalar(select(AssessmentSuite).where(AssessmentSuite.name == name, AssessmentSuite.organisation_id.is_(None)))
        if suite is None:
            suite = AssessmentSuite(
                organisation_id=None,
                industry_id=industries[industry_definition.sandbox].id,
                name=name,
                description=f"Versioned industry scenarios for {industry_definition.name.lower()} agents.",
            )
            db.add(suite)
            db.flush()
        suites[slug] = suite

    for scenario in SCENARIOS.values():
        content_hash = scenario.content_hash()
        definition = scenario.to_dict()
        payload = dict(
            suite_id=suites[scenario.industry].id,
            title=scenario.name,
            description=scenario.description,
            objective=scenario.objective,
            severity=scenario.risk,
            procedure=scenario.technique,
            is_platform=True,
            category=scenario.category,
            attack_scenario=scenario.description,
            test_input="\n\n".join(scenario.turns),
            expected_behaviour=scenario.secure,
            evaluation_criteria=" ".join(scenario.evaluation_criteria),
            evidence_requirements="Store every turn, reply, tool request, sandbox policy decision, state change, and check result.",
            remediation_guidance="\n".join(scenario.remediation),
            version=scenario.version,
            tags=[scenario.category, f"threat:{scenario.threat}", f"industry:{scenario.industry}"],
            requires_tools=scenario.requires_tools,
            kind="scenario",
            definition_json=definition,
            content_hash=content_hash,
        )
        existing = db.scalar(select(TestCase).where(TestCase.code == scenario.code))
        if existing is None:
            row = TestCase(organisation_id=None, code=scenario.code, **payload)
            row.industries = [industries[INDUSTRIES[scenario.industry].sandbox]]
            db.add(row)
            continue
        if existing.version == scenario.version and existing.content_hash not in {None, content_hash}:
            logger.warning("scenario_changed_without_version_bump code=%s version=%s", scenario.code, scenario.version)
        for key, value in payload.items():
            setattr(existing, key, value)
