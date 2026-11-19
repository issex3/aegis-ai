"""Redaction, export, and deletion of tenant data."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError
from app.models.agents import Agent, AgentCredential, AgentIntegration
from app.models.assessments import (
    Assessment,
    AssessmentComparison,
    AssessmentResult,
    Finding,
    FindingEvidence,
    FindingStatusEvent,
    Remediation,
    Report,
)
from app.models.base import utcnow
from app.models.identity import Organisation, OrganisationMembership, Session as DbSession, User
from app.models.intelligence import AssessmentSchedule, DataContributionConsent, WebhookEndpoint
from app.security import hash_session_token

SECRET_PATTERNS = (
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{16,}"),
    re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    re.compile(r"sk_test_[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-+=/]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|password|secret)\s*[:=]\s*\S+"),
)


def redact_text(value: str, extra: str | None = None) -> str:
    text = value
    if extra:
        for candidate in {extra, extra.strip()}:
            if candidate and candidate in text:
                text = text.replace(candidate, "[redacted-credential]")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def redact_structure(value: Any, extra: str | None = None) -> Any:
    if isinstance(value, str):
        return redact_text(value, extra)
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower() in {"secret", "password", "authorization", "ciphertext", "token", "api_key"}:
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = redact_structure(item, extra)
        return cleaned
    if isinstance(value, list):
        return [redact_structure(item, extra) for item in value]
    return value


def export_organisation(db: Session, organisation: Organisation) -> dict:
    agents = db.scalars(select(Agent).where(Agent.organisation_id == organisation.id, Agent.deleted_at.is_(None))).all()
    assessments = db.scalars(select(Assessment).where(Assessment.organisation_id == organisation.id)).all()
    findings = db.scalars(select(Finding).where(Finding.organisation_id == organisation.id)).all()
    reports = db.scalars(select(Report).where(Report.organisation_id == organisation.id)).all()
    members = db.scalars(select(OrganisationMembership).where(OrganisationMembership.organisation_id == organisation.id)).all()
    member_rows = []
    for membership in members:
        user = db.get(User, membership.user_id)
        member_rows.append(
            {
                "user_id": membership.user_id,
                "email": user.email if user else None,
                "full_name": user.full_name if user else None,
                "role": membership.role,
            }
        )
    return {
        "organisation": {"id": organisation.id, "name": organisation.name, "slug": organisation.slug},
        "exported_at": utcnow().isoformat(),
        "members": member_rows,
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "integration_type": agent.integration_type,
                "api_endpoint": agent.api_endpoint,
                "model_name": agent.model_name,
                "status": agent.status,
            }
            for agent in agents
        ],
        "assessments": [
            {
                "id": row.id,
                "name": row.name,
                "status": row.status,
                "agent_id": row.agent_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in assessments
        ],
        "findings": [
            {
                "id": row.id,
                "title": row.title,
                "severity": row.severity,
                "status": row.status,
                "assessment_id": row.assessment_id,
            }
            for row in findings
        ],
        "reports": [{"id": row.id, "assessment_id": row.assessment_id, "created_at": row.created_at.isoformat() if row.created_at else None} for row in reports],
        "note": "Credential secrets, session tokens, and MFA material are not included in this export.",
    }


def destroy_credential_rows(db: Session, organisation_id: str) -> int:
    rows = db.scalars(select(AgentCredential).where(AgentCredential.organisation_id == organisation_id)).all()
    count = 0
    for row in rows:
        row.ciphertext = f"deleted:{hash_session_token(row.ciphertext)[:32]}"
        row.hint = "gone"
        row.deleted_at = utcnow()
        count += 1
    return count


def delete_organisation_data(db: Session, settings: Settings, organisation: Organisation, *, actor_user_id: str) -> dict:
    """Irreversible tenant deletion. Audit events for the organisation are retained."""
    from app.commercial.models import AppNotification, AssessmentJob, IntelligenceApiKey, Subscription
    from app.models.intelligence import AuditEvent
    from app.scenarios.models import AgentProfile, AssessmentLog, TestingProgramme

    org_id = organisation.id
    destroyed_credentials = destroy_credential_rows(db, org_id)

    def _delete(model) -> int:
        rows = db.scalars(select(model).where(model.organisation_id == org_id)).all()
        count = len(rows)
        for row in rows:
            db.delete(row)
        return count

    counts = {
        "credentials_destroyed": destroyed_credentials,
        "credentials": _delete(AgentCredential),
        "finding_evidence": _delete(FindingEvidence),
        "finding_events": _delete(FindingStatusEvent),
        "remediation": _delete(Remediation),
        "findings": _delete(Finding),
        "assessment_results": _delete(AssessmentResult),
        "reports": _delete(Report),
        "comparisons": _delete(AssessmentComparison),
        "assessment_logs": _delete(AssessmentLog),
        "jobs": _delete(AssessmentJob),
        "assessments": _delete(Assessment),
        "programmes": _delete(TestingProgramme),
        "profiles": _delete(AgentProfile),
        "schedules": _delete(AssessmentSchedule),
        "webhooks": _delete(WebhookEndpoint),
        "integrations": _delete(AgentIntegration),
        "agents": _delete(Agent),
        "notifications": _delete(AppNotification),
        "licensed_keys": _delete(IntelligenceApiKey),
        "consent": _delete(DataContributionConsent),
        "sessions": _delete(DbSession),
    }
    subscription = db.scalar(select(Subscription).where(Subscription.organisation_id == org_id))
    if subscription is not None:
        db.delete(subscription)
        counts["subscriptions"] = 1
    memberships = db.scalars(select(OrganisationMembership).where(OrganisationMembership.organisation_id == org_id)).all()
    user_ids = [row.user_id for row in memberships]
    for membership in memberships:
        db.delete(membership)
    counts["memberships"] = len(memberships)
    organisation.deleted_at = utcnow()
    organisation.name = f"deleted-{organisation.id[:8]}"
    db.add(
        AuditEvent(
            organisation_id=None,
            actor_user_id=actor_user_id,
            action="organisation_deleted",
            resource_type="organisation",
            resource_id=org_id,
            ip_address=None,
            metadata_json={"counts": counts, "retention_days": getattr(organisation, "retention_days", None)},
        )
    )
    db.flush()
    for user_id in user_ids:
        remaining = db.scalar(
            select(OrganisationMembership).where(OrganisationMembership.user_id == user_id)
        )
        if remaining is None:
            user = db.get(User, user_id)
            if user is not None:
                user.email = f"deleted-{user.id}@invalid.example"
                user.full_name = "Deleted user"
                user.password_hash = hash_session_token(f"deleted:{user.id}:{settings.encryption_key}")
                user.mfa_secret_ciphertext = None
                user.mfa_recovery_hashes = []
                user.mfa_enabled = False
                user.is_active = False
    db.commit()
    return counts


def parse_export(raw: dict) -> str:
    return json.dumps(raw, default=str, indent=2)
