import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError
from app.integrations.registry import adapter_availability
from app.models.agents import Agent, AgentCredential, AgentIntegration
from app.models.assessments import Assessment, Finding, Report
from app.models.base import ensure_utc, utcnow
from app.models.identity import Organisation, OrganisationMembership, Session as DbSession, User
from app.models.intelligence import AuditEvent, DataContributionConsent, IntelligenceDataset
from app.models.sandboxes import Industry, Sandbox, SandboxVersion
from app.schemas import (
    CONSENT_POLICY_VERSION,
    CONSENT_SCOPE,
    AgentOut,
    AgentWrite,
    AssessmentOut,
    AuditEventOut,
    ConsentOut,
    CredentialOut,
    DashboardSummary,
    DatasetOut,
    FindingOut,
    IndustryOut,
    OrganisationOut,
    ReportOut,
    SandboxOut,
    SessionOut,
    UserOut,
    public_credential,
)
from app.security import (
    audit_digest,
    credential_hint,
    decrypt_secret,
    encrypt_secret,
    endpoint_origin,
    hash_password,
    hash_session_token,
    new_session_token,
    scrub_metadata,
    session_expiry,
    slugify,
    verify_password,
    verify_password_dummy,
)
from app.security_log import security_event

logger = logging.getLogger("aegis")

def canonical_role(role: str) -> str:
    return {"admin": "administrator", "member": "analyst"}.get(role, role)


WRITE_ROLES = {"owner", "administrator", "analyst"}
ADMIN_ROLE_SET = {"owner", "administrator"}
OWNER_ROLES = {"owner"}


def client_ip(request_client_host: str | None) -> str | None:
    if not request_client_host:
        return None
    return request_client_host[:64]


def record_audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    organisation_id: str | None = None,
    actor_user_id: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
) -> None:
    cleaned = scrub_metadata(metadata)
    previous = db.scalar(
        select(AuditEvent.event_hash)
        .where(AuditEvent.organisation_id == organisation_id)
        .where(AuditEvent.event_hash.is_not(None))
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    digest = audit_digest(
        {
            "previous": previous or "genesis",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "organisation_id": organisation_id,
            "actor_user_id": actor_user_id,
            "metadata": cleaned,
            "created_at": utcnow().isoformat(),
        }
    )
    db.add(
        AuditEvent(
            organisation_id=organisation_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            metadata_json=cleaned,
            previous_hash=previous,
            event_hash=digest,
        )
    )
    security_event(
        action,
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        ip_address=ip_address,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="recorded",
    )


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while db.scalar(select(Organisation.id).where(Organisation.slug == slug)):
        slug = f"{base[:40]}-{suffix}"
        suffix += 1
    return slug


def register_user(
    db: Session,
    settings: Settings,
    *,
    full_name: str,
    email: str,
    password: str,
    organisation_name: str,
    user_agent: str | None,
    ip_address: str | None,
    invite_token: str | None = None,
) -> tuple[str, SessionOut]:
    from app.iam import consume_invite, canonical_role

    existing = db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        verify_password_dummy(password)
        raise AppError(409, "email_in_use", "An account with that email already exists.")

    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        mfa_recovery_hashes=[],
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    if invite_token:
        invite = consume_invite(db, invite_token)
        if invite.email != user.email:
            raise AppError(400, "invalid_invite", "That invitation is not valid.")
        organisation = db.get(Organisation, invite.organisation_id)
        if organisation is None or organisation.deleted_at is not None:
            raise AppError(400, "invalid_invite", "That invitation is not valid.")
        role = canonical_role(invite.role)
        invite.accepted_at = utcnow()
        membership = OrganisationMembership(organisation_id=organisation.id, user_id=user.id, role=role)
        db.add(membership)
    else:
        organisation = Organisation(
            name=organisation_name,
            slug=unique_slug(db, organisation_name),
            retention_days=settings.default_retention_days,
        )
        db.add(organisation)
        db.flush()
        membership = OrganisationMembership(organisation_id=organisation.id, user_id=user.id, role="owner")
        db.add(membership)
        role = "owner"
    token = issue_session(
        db,
        settings,
        user=user,
        organisation=organisation,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    record_audit(
        db,
        action="user_registered",
        resource_type="user",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
        metadata={"joined_via_invite": bool(invite_token)},
    )
    db.commit()
    return token, SessionOut(user=UserOut.model_validate(user), organisation=OrganisationOut.model_validate(organisation), role=role)


def authenticate(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    user_agent: str | None,
    ip_address: str | None,
):
    from app.iam import account_locked, clear_failed_logins, create_mfa_challenge, register_failed_login

    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is not None and account_locked(user):
        verify_password_dummy(password)
        record_audit(
            db,
            action="login_blocked_lockout",
            resource_type="session",
            actor_user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        raise AppError(429, "rate_limited", "Too many attempts. Wait a few minutes and try again.")
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        verify_password_dummy(password)
        register_failed_login(db, settings, user, ip_address)
        record_audit(
            db,
            action="login_failed",
            resource_type="session",
            actor_user_id=user.id if user else None,
            ip_address=ip_address,
            metadata={"email_domain": email.lower().split("@")[-1]},
        )
        db.commit()
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")

    if user.mfa_enabled:
        challenge = create_mfa_challenge(db, user, user_agent, ip_address)
        record_audit(
            db,
            action="login_mfa_required",
            resource_type="session",
            actor_user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        return None, {"mfa_required": True, "challenge_id": challenge}

    return authenticate_existing_user(db, settings, user, user_agent=user_agent, ip_address=ip_address)


def authenticate_existing_user(
    db: Session,
    settings: Settings,
    user: User,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, SessionOut]:
    from app.iam import clear_failed_logins

    membership = db.scalar(
        select(OrganisationMembership)
        .where(OrganisationMembership.user_id == user.id)
        .order_by(OrganisationMembership.created_at.asc())
    )
    if membership is None:
        raise AppError(403, "no_organisation", "This account is not a member of an organisation.")
    organisation = db.get(Organisation, membership.organisation_id)
    if organisation is None or organisation.deleted_at is not None:
        raise AppError(403, "no_organisation", "This account is not a member of an organisation.")
    clear_failed_logins(user)
    token = issue_session(
        db,
        settings,
        user=user,
        organisation=organisation,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    record_audit(
        db,
        action="login_succeeded",
        resource_type="session",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    return token, SessionOut(
        user=UserOut.model_validate(user),
        organisation=OrganisationOut.model_validate(organisation),
        role=membership.role,
    )


def issue_session(
    db: Session,
    settings: Settings,
    *,
    user: User,
    organisation: Organisation,
    user_agent: str | None,
    ip_address: str | None,
) -> str:
    token = new_session_token()
    db.add(
        DbSession(
            user_id=user.id,
            organisation_id=organisation.id,
            token_hash=hash_session_token(token),
            expires_at=session_expiry(settings.session_ttl_hours),
            last_seen_at=utcnow(),
            user_agent=(user_agent or "")[:256] or None,
            ip_address=ip_address,
        )
    )
    return token


def revoke_session(db: Session, token: str | None, ip_address: str | None) -> None:
    if not token:
        return
    record = db.scalar(select(DbSession).where(DbSession.token_hash == hash_session_token(token)))
    if record and record.revoked_at is None:
        record.revoked_at = utcnow()
        record_audit(
            db,
            action="logout",
            resource_type="session",
            organisation_id=record.organisation_id,
            actor_user_id=record.user_id,
            resource_id=record.id,
            ip_address=ip_address,
        )
        db.commit()


def resolve_session(db: Session, token: str | None) -> tuple[User, Organisation, OrganisationMembership, DbSession]:
    if not token:
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    record = db.scalar(select(DbSession).where(DbSession.token_hash == hash_session_token(token)))
    now = utcnow()
    if record is None or record.revoked_at is not None or ensure_utc(record.expires_at) <= now or record.organisation_id is None:
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    last_seen = ensure_utc(record.last_seen_at) if record.last_seen_at else ensure_utc(record.created_at)
    if last_seen + timedelta(hours=settings_idle_hours()) <= now:
        record.revoked_at = now
        db.commit()
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    user = db.get(User, record.user_id)
    organisation = db.get(Organisation, record.organisation_id)
    if user is None or organisation is None or not user.is_active or organisation.deleted_at is not None:
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    record.last_seen_at = now
    membership = db.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == user.id,
            OrganisationMembership.organisation_id == organisation.id,
        )
    )
    if membership is None:
        raise AppError(403, "forbidden", "You do not have access to this organisation.")
    return user, organisation, membership, record


def settings_idle_hours() -> int:
    from app.config import get_settings

    return get_settings().session_idle_hours


def require_role(membership: OrganisationMembership, roles: set[str]) -> None:
    from app.config import get_settings
    from app.iam import require_admin_mfa

    allowed = {canonical_role(role) for role in roles}
    if canonical_role(membership.role) not in allowed:
        security_event(
            "authorisation_denied",
            organisation_id=membership.organisation_id,
            actor_user_id=membership.user_id,
            outcome="denied",
            required_roles=sorted(allowed),
            actual_role=canonical_role(membership.role),
        )
        raise AppError(403, "forbidden", "You do not have permission to perform this action.")
    require_admin_mfa(membership.user, membership, get_settings(), set(roles))


def active_credential(db: Session, agent_id: str) -> AgentCredential | None:
    return db.scalar(
        select(AgentCredential)
        .where(AgentCredential.agent_id == agent_id, AgentCredential.deleted_at.is_(None))
        .order_by(AgentCredential.created_at.desc())
    )


def to_agent_out(db: Session, agent: Agent) -> AgentOut:
    credential = active_credential(db, agent.id)
    credential_out: CredentialOut
    if credential is None:
        credential_out = public_credential(None, None)
    else:
        credential_out = public_credential(credential.hint, credential.rotated_at or credential.created_at)
    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        integration_type=agent.integration_type,
        api_endpoint=agent.api_endpoint,
        model_name=agent.model_name,
        purpose=agent.purpose,
        behaviour=agent.behaviour,
        security_boundaries=agent.security_boundaries,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        credential=credential_out,
        timeout_seconds=agent.integration.timeout_seconds if agent.integration else 30,
        max_output_tokens=agent.integration.max_output_tokens if agent.integration else 512,
        temperature=agent.integration.temperature if agent.integration else None,
        adapter_status=adapter_availability(agent.integration_type),
        demo_profile=((agent.integration.config_json or {}).get("weakness_profile", "default") if agent.integration else "default")
        if agent.integration_type == "aegis_demo"
        else None,
    )


def get_agent(db: Session, organisation_id: str, agent_id: str, *, actor_user_id: str | None = None, ip_address: str | None = None) -> Agent:
    agent = db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organisation_id == organisation_id,
            Agent.deleted_at.is_(None),
        )
    )
    if agent is None:
        other = db.scalar(select(Agent.id).where(Agent.id == agent_id))
        if other:
            record_audit(
                db,
                action="cross_tenant_denied",
                resource_type="agent",
                organisation_id=organisation_id,
                actor_user_id=actor_user_id,
                resource_id=agent_id,
                ip_address=ip_address,
            )
            db.commit()
            security_event(
                "cross_tenant_denied",
                organisation_id=organisation_id,
                actor_user_id=actor_user_id,
                ip_address=ip_address,
                resource_type="agent",
                outcome="denied",
            )
        raise AppError(404, "not_found", "Agent not found.")
    return agent


def list_agents(db: Session, organisation_id: str) -> list[AgentOut]:
    agents = db.scalars(
        select(Agent)
        .where(Agent.organisation_id == organisation_id, Agent.deleted_at.is_(None))
        .order_by(Agent.created_at.desc())
    ).all()
    return [to_agent_out(db, agent) for agent in agents]


def _sync_integration(db: Session, agent: Agent, payload: AgentWrite | None = None) -> None:
    integration = agent.integration
    timeout = payload.timeout_seconds if payload else 30
    max_tokens = payload.max_output_tokens if payload else 512
    temperature = payload.temperature if payload else None
    if integration is None:
        db.add(
            AgentIntegration(
                agent_id=agent.id,
                organisation_id=agent.organisation_id,
                provider=agent.integration_type,
                endpoint=agent.api_endpoint,
                model_name=agent.model_name,
                timeout_seconds=timeout,
                max_output_tokens=max_tokens,
                temperature=temperature,
                config_json={},
            )
        )
        return
    integration.provider = agent.integration_type
    integration.endpoint = agent.api_endpoint
    integration.model_name = agent.model_name
    integration.organisation_id = agent.organisation_id
    integration.timeout_seconds = timeout
    integration.max_output_tokens = max_tokens
    integration.temperature = temperature
    integration.updated_at = utcnow()


def store_credential(
    db: Session,
    settings: Settings,
    *,
    agent: Agent,
    secret: str,
    actor_user_id: str,
    ip_address: str | None,
    rotate: bool,
) -> None:
    current = active_credential(db, agent.id)
    now = utcnow()
    if current is not None:
        current.deleted_at = now
        current.ciphertext = encrypt_secret_placeholder(current.ciphertext)
    db.add(
        AgentCredential(
            agent_id=agent.id,
            organisation_id=agent.organisation_id,
            ciphertext=encrypt_secret(settings, secret, agent.organisation_id),
            hint=credential_hint(secret),
            rotated_at=now if rotate or current is not None else None,
        )
    )
    record_audit(
        db,
        action="credential_rotated" if current is not None else "credential_stored",
        resource_type="agent_credential",
        organisation_id=agent.organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
        metadata={"rotated": current is not None},
    )
    logger.info("credential_written agent_id=%s organisation_id=%s", agent.id, agent.organisation_id)


def delete_credential(
    db: Session,
    *,
    agent: Agent,
    actor_user_id: str,
    ip_address: str | None,
) -> None:
    current = active_credential(db, agent.id)
    if current is None:
        raise AppError(404, "not_found", "No credential is stored for this agent.")
    current.deleted_at = utcnow()
    current.ciphertext = encrypt_secret_placeholder(current.ciphertext)
    record_audit(
        db,
        action="credential_deleted",
        resource_type="agent_credential",
        organisation_id=agent.organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
    )


def encrypt_secret_placeholder(existing: str) -> str:
    """Destroy recoverable key material while keeping the row for audit linkage."""
    return f"deleted:{hash_session_token(existing)[:32]}"


def load_credential_secret(db: Session, settings: Settings, agent: Agent) -> str:
    """Server-side only. Not exposed by an API route."""
    current = active_credential(db, agent.id)
    if current is None:
        raise AppError(404, "not_found", "No credential is stored for this agent.")
    return decrypt_secret(settings, current.ciphertext, agent.organisation_id)


def create_agent(
    db: Session,
    settings: Settings,
    *,
    organisation_id: str,
    actor_user_id: str,
    payload: AgentWrite,
    ip_address: str | None,
) -> AgentOut:
    from app.commercial.billing import enforce_agent_limit

    enforce_agent_limit(db, settings, organisation_id)
    agent = Agent(
        organisation_id=organisation_id,
        created_by_user_id=actor_user_id,
        name=payload.name,
        description=payload.description,
        integration_type=payload.integration_type,
        api_endpoint=payload.api_endpoint,
        model_name=payload.model_name,
        purpose=payload.purpose,
        behaviour=payload.behaviour,
        security_boundaries=payload.security_boundaries,
        status="active",
    )
    db.add(agent)
    db.flush()
    _sync_integration(db, agent, payload)
    if payload.secret:
        store_credential(
            db,
            settings,
            agent=agent,
            secret=payload.secret,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            rotate=False,
        )
    record_audit(
        db,
        action="agent_created",
        resource_type="agent",
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
        metadata={"integration_type": payload.integration_type},
    )
    db.commit()
    db.refresh(agent)
    return to_agent_out(db, agent)


def update_agent(
    db: Session,
    *,
    agent: Agent,
    payload: AgentWrite,
    actor_user_id: str,
    ip_address: str | None,
) -> AgentOut:
    origin_changed = endpoint_origin(agent.api_endpoint) != endpoint_origin(payload.api_endpoint)
    agent.name = payload.name
    agent.description = payload.description
    agent.integration_type = payload.integration_type
    agent.api_endpoint = payload.api_endpoint
    agent.model_name = payload.model_name
    agent.purpose = payload.purpose
    agent.behaviour = payload.behaviour
    agent.security_boundaries = payload.security_boundaries
    agent.updated_at = utcnow()
    _sync_integration(db, agent, payload)
    if origin_changed:
        current = active_credential(db, agent.id)
        if current is not None:
            current.deleted_at = utcnow()
            current.ciphertext = encrypt_secret_placeholder(current.ciphertext)
            record_audit(
                db,
                action="credential_revoked_origin_change",
                resource_type="agent_credential",
                organisation_id=agent.organisation_id,
                actor_user_id=actor_user_id,
                resource_id=agent.id,
                ip_address=ip_address,
                metadata={"new_origin": endpoint_origin(payload.api_endpoint)},
            )
    record_audit(
        db,
        action="agent_updated",
        resource_type="agent",
        organisation_id=agent.organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
        metadata={"origin_changed": origin_changed},
    )
    db.commit()
    db.refresh(agent)
    return to_agent_out(db, agent)


def set_agent_status(
    db: Session,
    *,
    agent: Agent,
    status: str,
    actor_user_id: str,
    ip_address: str | None,
) -> AgentOut:
    agent.status = status
    agent.updated_at = utcnow()
    record_audit(
        db,
        action="agent_disabled" if status == "disabled" else "agent_enabled",
        resource_type="agent",
        organisation_id=agent.organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(agent)
    return to_agent_out(db, agent)


def delete_agent(
    db: Session,
    *,
    agent: Agent,
    actor_user_id: str,
    ip_address: str | None,
) -> None:
    now = utcnow()
    agent.deleted_at = now
    agent.status = "disabled"
    agent.updated_at = now
    credentials = db.scalars(select(AgentCredential).where(AgentCredential.agent_id == agent.id)).all()
    for credential in credentials:
        credential.deleted_at = credential.deleted_at or now
        if not credential.ciphertext.startswith("deleted:"):
            credential.ciphertext = encrypt_secret_placeholder(credential.ciphertext)
    record_audit(
        db,
        action="agent_deleted",
        resource_type="agent",
        organisation_id=agent.organisation_id,
        actor_user_id=actor_user_id,
        resource_id=agent.id,
        ip_address=ip_address,
    )
    db.commit()
    logger.info("agent_deleted agent_id=%s", agent.id)


def assessment_out(db: Session, assessment: Assessment) -> AssessmentOut:
    agent = db.get(Agent, assessment.agent_id)
    return AssessmentOut(
        id=assessment.id,
        agent_id=assessment.agent_id,
        agent_name=agent.name if agent else "Removed agent",
        name=assessment.name,
        status=assessment.status,
        created_at=assessment.created_at,
        started_at=assessment.started_at,
        completed_at=assessment.completed_at,
    )


def list_assessments(db: Session, organisation_id: str, agent_id: str | None = None) -> list[AssessmentOut]:
    query = select(Assessment).where(Assessment.organisation_id == organisation_id)
    if agent_id:
        query = query.where(Assessment.agent_id == agent_id)
    rows = db.scalars(query.order_by(Assessment.created_at.desc())).all()
    return [assessment_out(db, row) for row in rows]


def create_draft_assessment(
    db: Session,
    *,
    organisation_id: str,
    actor_user_id: str,
    agent_id: str,
    name: str,
    ip_address: str | None,
) -> AssessmentOut:
    agent = get_agent(db, organisation_id, agent_id)
    if agent.status != "active":
        raise AppError(409, "agent_disabled", "Enable the agent before creating an assessment.")
    assessment = Assessment(
        organisation_id=organisation_id,
        agent_id=agent.id,
        name=name,
        status="draft",
        created_by_user_id=actor_user_id,
    )
    db.add(assessment)
    db.flush()
    record_audit(
        db,
        action="assessment_draft_created",
        resource_type="assessment",
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        resource_id=assessment.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(assessment)
    return assessment_out(db, assessment)


def list_findings(db: Session, organisation_id: str) -> list[FindingOut]:
    rows = db.scalars(
        select(Finding).where(Finding.organisation_id == organisation_id).order_by(Finding.created_at.desc())
    ).all()
    return [
        FindingOut(
            id=row.id,
            title=row.title,
            severity=row.severity,
            status=row.status,
            category=row.category or "",
            confidence=row.confidence or "medium",
            stable_key=row.stable_key,
            agent_id=row.agent_id,
            assessment_id=row.assessment_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def list_reports(db: Session, organisation_id: str) -> list[ReportOut]:
    rows = db.scalars(
        select(Report).where(Report.organisation_id == organisation_id).order_by(Report.created_at.desc())
    ).all()
    return [
        ReportOut(
            id=row.id,
            title=row.title,
            status=row.status,
            assessment_id=row.assessment_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def list_industries(db: Session) -> list[IndustryOut]:
    rows = db.scalars(select(Industry).order_by(Industry.name.asc())).all()
    return [IndustryOut.model_validate(row) for row in rows]


def list_visible_sandboxes(db: Session, organisation_id: str) -> list[SandboxOut]:
    rows = db.scalars(
        select(Sandbox)
        .where((Sandbox.organisation_id.is_(None)) | (Sandbox.organisation_id == organisation_id))
        .order_by(Sandbox.name.asc())
    ).all()
    results: list[SandboxOut] = []
    for sandbox in rows:
        industry = db.get(Industry, sandbox.industry_id)
        version_number = None
        if sandbox.current_version_id:
            version = db.get(SandboxVersion, sandbox.current_version_id)
            version_number = version.version_number if version else None
        results.append(
            SandboxOut(
                id=sandbox.id,
                name=sandbox.name,
                description=sandbox.description,
                status=sandbox.status,
                industry_name=industry.name if industry else "Unknown",
                current_version_number=version_number,
            )
        )
    return results


def latest_consent(db: Session, organisation_id: str) -> ConsentOut:
    row = db.scalar(
        select(DataContributionConsent)
        .where(
            DataContributionConsent.organisation_id == organisation_id,
            DataContributionConsent.scope == CONSENT_SCOPE,
        )
        .order_by(DataContributionConsent.recorded_at.desc())
    )
    if row is None:
        return ConsentOut(granted=False, policy_version=CONSENT_POLICY_VERSION, scope=CONSENT_SCOPE, recorded_at=None)
    return ConsentOut(
        granted=row.granted and row.revoked_at is None,
        policy_version=row.policy_version,
        scope=row.scope,
        recorded_at=row.recorded_at,
        permitted_categories=list(row.permitted_categories or []),
        intended_use=row.intended_use or "",
    )


def record_consent(
    db: Session,
    *,
    organisation_id: str,
    user_id: str,
    granted: bool,
    ip_address: str | None,
    permitted_categories: list[str] | None = None,
    intended_use: str = "",
) -> ConsentOut:
    now = utcnow()
    previous = db.scalar(
        select(DataContributionConsent)
        .where(
            DataContributionConsent.organisation_id == organisation_id,
            DataContributionConsent.scope == CONSENT_SCOPE,
            DataContributionConsent.revoked_at.is_(None),
            DataContributionConsent.granted.is_(True),
        )
        .order_by(DataContributionConsent.recorded_at.desc())
    )
    if previous is not None and not granted:
        previous.revoked_at = now
    row = DataContributionConsent(
        organisation_id=organisation_id,
        user_id=user_id,
        policy_version=CONSENT_POLICY_VERSION,
        scope=CONSENT_SCOPE,
        permitted_categories=list(permitted_categories or []),
        intended_use=intended_use,
        granted=granted,
        recorded_at=now,
        revoked_at=None if granted else now,
    )
    db.add(row)
    record_audit(
        db,
        action="consent_recorded",
        resource_type="data_contribution_consent",
        organisation_id=organisation_id,
        actor_user_id=user_id,
        resource_id=row.id,
        ip_address=ip_address,
        metadata={"granted": granted, "policy_version": CONSENT_POLICY_VERSION, "scope": CONSENT_SCOPE, "categories": list(permitted_categories or [])},
    )
    db.commit()
    db.refresh(row)
    return ConsentOut(
        granted=row.granted and row.revoked_at is None,
        policy_version=row.policy_version,
        scope=row.scope,
        recorded_at=row.recorded_at,
        permitted_categories=list(row.permitted_categories or []),
        intended_use=row.intended_use or "",
    )


def list_datasets_for_operator(db: Session) -> list[DatasetOut]:
    from app.models.intelligence import DatasetVersion

    datasets = db.scalars(select(IntelligenceDataset).order_by(IntelligenceDataset.name.asc())).all()
    results = []
    for dataset in datasets:
        version_count = db.scalar(
            select(func.count()).select_from(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id)
        )
        results.append(
            DatasetOut(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                classification=dataset.classification,
                version_count=int(version_count or 0),
            )
        )
    return results


def list_audit_events(db: Session, organisation_id: str, limit: int = 20) -> list[AuditEventOut]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.organisation_id == organisation_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        AuditEventOut(
            id=row.id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def dashboard_summary(db: Session, organisation_id: str) -> DashboardSummary:
    agents = db.scalars(
        select(Agent).where(Agent.organisation_id == organisation_id, Agent.deleted_at.is_(None))
    ).all()
    assessments = db.scalars(select(Assessment).where(Assessment.organisation_id == organisation_id)).all()
    findings = db.scalars(select(Finding).where(Finding.organisation_id == organisation_id)).all()
    report_count = db.scalar(select(func.count()).select_from(Report).where(Report.organisation_id == organisation_id)) or 0

    status_counts: dict[str, int] = {}
    for assessment in assessments:
        status_counts[assessment.status] = status_counts.get(assessment.status, 0) + 1
    severity_counts: dict[str, int] = {}
    open_findings = 0
    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        if finding.status == "open":
            open_findings += 1

    recent = sorted(assessments, key=lambda item: item.created_at, reverse=True)[:5]
    from app.intelligence.scoring import WEIGHTS, score_assessment
    from app.models.assessments import AssessmentComparison, AssessmentResult
    from app.models.sandboxes import Sandbox, SandboxVersion

    completed = sorted((item for item in assessments if item.status == "completed"), key=lambda item: item.created_at)
    posture = None
    if completed:
        latest = completed[-1]
        result_rows = db.scalars(select(AssessmentResult).where(AssessmentResult.assessment_id == latest.id)).all()
        finding_by_result = {finding.result_id: finding for finding in findings if finding.assessment_id == latest.id}
        ordered = sorted(result_rows, key=lambda row: row.created_at)
        weights = []
        for row in ordered:
            if row.status == "FAIL":
                finding = finding_by_result.get(row.id)
                weights.append(WEIGHTS.get(finding.severity if finding else "medium", 4))
        scored = score_assessment([{"status": row.status} for row in ordered], weights)
        history = []
        for item in completed[-8:]:
            rows = db.scalars(select(AssessmentResult).where(AssessmentResult.assessment_id == item.id)).all()
            item_weights = []
            linked = {finding.result_id: finding for finding in findings if finding.assessment_id == item.id}
            for row in sorted(rows, key=lambda entry: entry.created_at):
                if row.status == "FAIL":
                    found = linked.get(row.id)
                    item_weights.append(WEIGHTS.get(found.severity if found else "medium", 4))
            ordered_rows = sorted(rows, key=lambda entry: entry.created_at)
            item_score = score_assessment([{"status": row.status} for row in ordered_rows], item_weights)
            history.append({"assessment_id": item.id, "name": item.name, "score": item_score["score"], "created_at": item.created_at.isoformat()})
        industry_counts: dict[str, int] = {}
        for finding in findings:
            label = "unscoped"
            if finding.sandbox_version_id:
                version = db.get(SandboxVersion, finding.sandbox_version_id)
                sandbox = db.get(Sandbox, version.sandbox_id) if version else None
                label = sandbox.name if sandbox else "unscoped"
            industry_counts[label] = industry_counts.get(label, 0) + 1
        comparisons = db.scalars(
            select(AssessmentComparison).where(AssessmentComparison.organisation_id == organisation_id).order_by(AssessmentComparison.created_at.desc())
        ).all()
        latest_regression = comparisons[0].details_json if comparisons else {}
        posture = {
            **scored,
            "history": history,
            "findings_by_severity": severity_counts,
            "findings_by_sandbox": industry_counts,
            "resolved": sum(1 for finding in findings if finding.status == "resolved"),
            "open": open_findings,
            "regression": latest_regression.get("counts", {}) if isinstance(latest_regression, dict) else {},
            "baselines": sum(1 for item in assessments if item.is_baseline),
        }
    return DashboardSummary(
        agents={
            "total": len(agents),
            "active": sum(1 for agent in agents if agent.status == "active"),
            "disabled": sum(1 for agent in agents if agent.status == "disabled"),
        },
        assessments={"total": len(assessments), "by_status": status_counts},
        findings={"total": len(findings), "open": open_findings, "by_severity": severity_counts},
        reports={"total": int(report_count)},
        recent_assessments=[assessment_out(db, item) for item in recent],
        recent_audit_events=list_audit_events(db, organisation_id, limit=8),
        posture=posture,
    )


def update_profile(db: Session, user: User, full_name: str, ip_address: str | None, organisation_id: str) -> UserOut:
    user.full_name = full_name
    user.updated_at = utcnow()
    record_audit(
        db,
        action="profile_updated",
        resource_type="user",
        organisation_id=organisation_id,
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def change_password(
    db: Session,
    user: User,
    *,
    current_password: str,
    new_password: str,
    organisation_id: str,
    ip_address: str | None,
    current_session_id: str | None = None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AppError(400, "invalid_password", "The current password is incorrect.")
    if current_password == new_password:
        raise AppError(400, "password_unchanged", "Choose a different password.")
    user.password_hash = hash_password(new_password)
    user.updated_at = utcnow()
    from app.iam import revoke_user_sessions

    revoked = revoke_user_sessions(db, user.id, except_id=current_session_id)
    record_audit(
        db,
        action="password_changed",
        resource_type="user",
        organisation_id=organisation_id,
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
        metadata={"sessions_revoked": revoked},
    )
    db.commit()


def update_organisation(
    db: Session,
    organisation: Organisation,
    *,
    name: str,
    actor_user_id: str,
    ip_address: str | None,
) -> OrganisationOut:
    organisation.name = name
    organisation.updated_at = utcnow()
    record_audit(
        db,
        action="organisation_updated",
        resource_type="organisation",
        organisation_id=organisation.id,
        actor_user_id=actor_user_id,
        resource_id=organisation.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(organisation)
    return OrganisationOut.model_validate(organisation)

