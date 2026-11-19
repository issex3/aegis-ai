"""Prepare contributed records from observed outcomes. Customer replies are not copied."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.intelligence.sanitise import find_sensitive
from app.models.agents import Agent
from app.models.assessments import Assessment, Finding, TestCase
from app.models.base import utcnow
from app.models.identity import Organisation
from app.models.intelligence import DataContributionConsent, DatasetVersion, IntelligenceDataset, IntelligenceRecord
from app.models.sandboxes import SandboxVersion
from app.services import latest_consent

PROCESSING_VERSION = "2026.11"
REQUIRED = ("industry_category", "test_category", "attack_technique", "synthetic_attack_input", "expected_security_behaviour", "observed_outcome", "severity", "evidence_quality")


def _dataset_version(db: Session) -> DatasetVersion:
    dataset = db.scalar(select(IntelligenceDataset).where(IntelligenceDataset.name == "Aegis evaluation corpus"))
    if dataset is None:
        dataset = IntelligenceDataset(
            name="Aegis evaluation corpus",
            description="Contributed evaluation outcomes approved for licensing review. Customer content is not included.",
            classification="restricted",
        )
        db.add(dataset)
        db.flush()
    version = db.scalar(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id, DatasetVersion.version_label == PROCESSING_VERSION)
    )
    if version is None:
        version = DatasetVersion(dataset_id=dataset.id, version_label=PROCESSING_VERSION, status="draft", notes="Awaiting approved records.")
        db.add(version)
        db.flush()
    return version


def contribute_assessment(db: Session, organisation_id: str, assessment_id: str) -> dict:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.organisation_id == organisation_id))
    if assessment is None or assessment.status != "completed":
        return {"accepted": 0, "rejected": [{"reason": "assessment_not_completed"}]}
    consent_view = latest_consent(db, organisation_id)
    consent = db.scalar(
        select(DataContributionConsent)
        .where(DataContributionConsent.organisation_id == organisation_id)
        .order_by(DataContributionConsent.recorded_at.desc())
    )
    if not consent_view.granted or consent is None:
        return {"accepted": 0, "rejected": [{"reason": "consent_not_granted"}]}
    permitted = set(consent.permitted_categories or [])
    if not permitted:
        return {"accepted": 0, "rejected": [{"reason": "no_permitted_categories"}]}
    organisation = db.get(Organisation, organisation_id)
    agent = db.get(Agent, assessment.agent_id)
    version = _dataset_version(db)
    findings = db.scalars(
        select(Finding).where(Finding.assessment_id == assessment.id, Finding.organisation_id == organisation_id)
    ).all()
    accepted = 0
    rejected = []
    for finding in findings:
        if finding.category not in permitted:
            rejected.append({"finding_id": finding.id, "reason": "category_not_permitted"})
            continue
        case = db.get(TestCase, finding.test_case_id) if finding.test_case_id else None
        if case is None:
            rejected.append({"finding_id": finding.id, "reason": "missing_test_case"})
            continue
        sandbox_version = db.get(SandboxVersion, finding.sandbox_version_id) if finding.sandbox_version_id else None
        industry_slug = "generic"
        if sandbox_version is not None:
            from app.models.sandboxes import Sandbox

            sandbox = db.get(Sandbox, sandbox_version.sandbox_id)
            if sandbox is not None:
                from app.models.sandboxes import Industry

                industry = db.get(Industry, sandbox.industry_id)
                industry_slug = industry.slug if industry else "generic"
        observed = {
            "outcome": "fail",
            "severity": finding.severity,
            "confidence": finding.confidence,
            "tool_requested": "tool" in (finding.actual_behaviour or "").lower() or finding.confidence == "high",
        }
        record = {
            "industry_category": industry_slug,
            "agent_framework_category": agent.integration_type if agent else "unknown",
            "model_identifier": agent.model_name if agent and agent.integration_type == "aegis_demo" else "withheld",
            "test_category": finding.category,
            "attack_technique": case.code,
            "synthetic_attack_input": case.test_input,
            "expected_security_behaviour": case.expected_behaviour,
            "observed_outcome": "fail",
            "normalised_vulnerability_category": finding.category,
            "severity": finding.severity,
            "evidence_quality": finding.confidence,
            "evaluation_confidence": finding.confidence,
            "remediation_category": finding.category,
            "retest_outcome": None,
            "test_case_version": case.version,
            "sandbox_version": sandbox_version.version_number if sandbox_version else None,
            "observed_facts": observed,
            "inferred": {"severity_rule": finding.severity_rule},
        }
        reasons = find_sensitive(record, organisation.name if organisation else "", agent.api_endpoint if agent else "")
        missing = [key for key in REQUIRED if record.get(key) in (None, "")]
        if reasons or missing:
            rejected.append({"finding_id": finding.id, "reason": "rejected", "detail": reasons or missing})
            continue
        duplicate = db.scalar(
            select(IntelligenceRecord).where(
                IntelligenceRecord.source_finding_id == finding.id,
                IntelligenceRecord.dataset_version_id == version.id,
            )
        )
        if duplicate is not None:
            rejected.append({"finding_id": finding.id, "reason": "duplicate"})
            continue
        db.add(
            IntelligenceRecord(
                dataset_version_id=version.id,
                source_organisation_id=organisation_id,
                source_consent_id=consent.id,
                source_finding_id=finding.id,
                redacted_summary=f"{case.code} observed fail ({finding.severity}). Customer response text was not stored.",
                record_json=record,
                validation_status="pending_review",
                approval_status="unapproved",
                processing_version=PROCESSING_VERSION,
                provenance_json={
                    "assessment_id": assessment.id,
                    "consent_id": consent.id,
                    "test_case_version": case.version,
                    "sandbox_version_id": finding.sandbox_version_id,
                    "processing_version": PROCESSING_VERSION,
                    "created_at": utcnow().isoformat(),
                },
            )
        )
        accepted += 1
    db.commit()
    return {"accepted": accepted, "rejected": rejected, "validation_status": "pending_review" if accepted else "rejected"}
