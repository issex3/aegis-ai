import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import AppError
from app.engine.operations import (
    assessment_payload,
    cancel_assessment,
    create_demo_agent,
    plan_assessment,
    preview_cases,
    sandbox_payload,
    start_assessment,
    test_connection,
    visible_sandbox,
)
from app.intelligence.governance import (
    approve_record,
    assessment_score,
    compare_assessments,
    create_schedule,
    create_webhook,
    intelligence_summary,
    rerun_assessment,
    run_schedule,
    save_baseline,
    set_demo_profile,
    trigger_webhook,
    update_finding,
)
from app.intelligence.pipeline import contribute_assessment
from app.intelligence.remediation_catalogue import CATALOGUE
from app.engine.catalog import CATEGORIES
from app.sandboxes.definitions import SANDBOXES
from app.schemas import (
    ADMIN_ROLES,
    AgentStatusUpdate,
    AgentUpdate,
    AgentWrite,
    AssessmentCreate,
    AssessmentPlan,
    ConsentWrite,
    CredentialWrite,
    ForgotPasswordRequest,
    LabSessionCreate,
    LabToolInvoke,
    LicensedKeyCreate,
    LoginRequest,
    MemberInviteRequest,
    MemberRoleUpdate,
    MfaCodeRequest,
    MfaDisableRequest,
    MfaVerifyRequest,
    OrganisationRetentionUpdate,
    OrganisationUpdate,
    PasswordChangeRequest,
    ProfileUpdate,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.security import endpoint_origin
from app.security import CLIENT_HEADER, CLIENT_HEADER_VALUE
from app.services import (
    WRITE_ROLES,
    authenticate,
    change_password,
    client_ip,
    create_agent,
    create_draft_assessment,
    dashboard_summary,
    delete_agent,
    delete_credential,
    get_agent,
    latest_consent,
    list_agents,
    list_assessments,
    list_audit_events,
    list_datasets_for_operator,
    list_findings,
    list_industries,
    list_reports,
    list_visible_sandboxes,
    record_consent,
    register_user,
    require_role,
    resolve_session,
    revoke_session,
    set_agent_status,
    store_credential,
    to_agent_out,
    update_agent,
    update_organisation,
    update_profile,
)

router = APIRouter(prefix="/api/v1")
_attempts: dict[str, deque[float]] = defaultdict(deque)


def settings_dep() -> Settings:
    return get_settings()


def request_ip(request: Request, settings: Settings) -> str | None:
    peer = request.client.host if request.client else None
    trusted = {item.strip() for item in settings.trusted_proxy_ips.split(",") if item.strip()}
    if peer in trusted:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()[:64]
    return client_ip(peer)


def request_context(request: Request, settings: Settings | None = None) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    resolved = settings or get_settings()
    return user_agent, request_ip(request, resolved)


def enforce_client_header(request: Request) -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.headers.get(CLIENT_HEADER) != CLIENT_HEADER_VALUE:
            raise AppError(400, "invalid_client", "The request could not be accepted.")


def enforce_rate_limit(request: Request, settings: Settings, bucket: str, account: str | None = None) -> None:
    if not settings.auth_rate_limit_enabled:
        return
    identity = request_ip(request, settings) or "unknown"
    keys = [f"{bucket}:ip:{identity}"]
    limits = {keys[0]: settings.auth_rate_limit_ip}
    if account:
        account_key = f"{bucket}:acct:{account.lower()}"
        keys.append(account_key)
        limits[account_key] = settings.auth_rate_limit_account
    now = time.monotonic()
    for key in keys:
        window = _attempts[key]
        while window and now - window[0] > 600:
            window.popleft()
        if len(window) >= limits[key]:
            raise AppError(429, "rate_limited", "Too many attempts. Wait a few minutes and try again.")
        window.append(now)


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(key=settings.cookie_name, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure)


def current_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    enforce_client_header(request)
    token = request.cookies.get(settings.cookie_name)
    return resolve_session(db, token)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "checks": {"api": "ok"}}


@router.get("/billing/plans")
def billing_plans(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    from app.commercial.billing import get_subscription
    from app.commercial.plans import PLANS

    subscription = get_subscription(db, organisation.id)
    return {
        "plans": [{"code": code, **plan} for code, plan in PLANS.items()],
        "subscription": None
        if subscription is None
        else {"plan_code": subscription.plan_code, "status": subscription.status},
        "note": "Prices are initial hypotheses. Subscription status is updated only from verified Stripe webhooks.",
    }


@router.post("/billing/checkout")
def billing_checkout(payload: dict, principal=Depends(current_principal), settings: Settings = Depends(settings_dep)):
    user, organisation, membership, _session = principal
    from app.services import OWNER_ROLES, require_role

    require_role(membership, OWNER_ROLES)
    from app.commercial.billing import create_checkout

    url = create_checkout(settings, organisation.id, str(payload.get("plan_code") or ""))
    _ = user
    return {"url": url}


@router.post("/billing/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    from app.commercial.billing import apply_stripe_subscription, verify_webhook

    event = verify_webhook(settings, await request.body(), request.headers.get("stripe-signature"))
    data = event["data"]["object"]
    if event["type"] in {"customer.subscription.updated", "customer.subscription.deleted", "customer.subscription.created"}:
        metadata = data.get("metadata") or {}
        organisation_id = metadata.get("organisation_id")
        plan_code = metadata.get("plan_code") or "starter"
        status = "canceled" if event["type"].endswith("deleted") else data.get("status", "inactive")
        if organisation_id:
            apply_stripe_subscription(
                db,
                organisation_id=organisation_id,
                plan_code=plan_code,
                status=status,
                customer_id=data.get("customer"),
                subscription_id=data.get("id"),
            )
    return {"received": True}


@router.get("/notifications")
def notifications(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    from sqlalchemy import select
    from app.commercial.models import AppNotification

    rows = db.scalars(select(AppNotification).where(AppNotification.organisation_id == organisation.id).order_by(AppNotification.created_at.desc()).limit(20)).all()
    return [{"id": row.id, "title": row.title, "body": row.body, "kind": row.kind, "created_at": row.created_at} for row in rows]


@router.get("/admin/overview")
def admin_overview(principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, _session = principal
    if not user.is_platform_operator:
        raise AppError(403, "forbidden", "Platform administration is restricted.")
    from sqlalchemy import func, select
    from app.commercial.models import AssessmentJob
    from app.models.identity import Organisation
    from app.models.intelligence import IntelligenceRecord

    return {
        "organisations": db.scalar(select(func.count()).select_from(Organisation)) or 0,
        "failed_jobs": db.scalar(select(func.count()).select_from(AssessmentJob).where(AssessmentJob.status == "failed")) or 0,
        "pending_contributions": db.scalar(select(func.count()).select_from(IntelligenceRecord).where(IntelligenceRecord.validation_status == "pending_review")) or 0,
    }


@router.post("/licensed/keys", status_code=201)
def create_licensed_key(payload: LicensedKeyCreate, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    from app.services import OWNER_ROLES, require_role, record_audit

    require_role(membership, OWNER_ROLES)
    import secrets
    from datetime import timedelta
    from app.commercial.models import IntelligenceApiKey
    from app.models.base import utcnow
    from app.security import hash_session_token

    token = secrets.token_urlsafe(24)
    key = IntelligenceApiKey(
        organisation_id=organisation.id,
        name=payload.name[:120],
        prefix=token[:8],
        token_hash=hash_session_token(token),
        enabled=True,
        expires_at=utcnow() + timedelta(days=365),
    )
    db.add(key)
    db.flush()
    _, ip_address = request_context(request)
    record_audit(
        db,
        action="licensed_key_created",
        resource_type="intelligence_api_key",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        resource_id=key.id,
        ip_address=ip_address,
    )
    db.commit()
    return {"id": key.id, "token": token, "prefix": token[:8], "expires_at": key.expires_at}


@router.get("/licensed/keys")
def list_licensed_keys(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    from app.services import OWNER_ROLES, require_role
    from sqlalchemy import select
    from app.commercial.models import IntelligenceApiKey

    require_role(membership, OWNER_ROLES)
    rows = db.scalars(
        select(IntelligenceApiKey).where(IntelligenceApiKey.organisation_id == organisation.id).order_by(IntelligenceApiKey.created_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "prefix": row.prefix,
            "enabled": row.enabled and row.revoked_at is None,
            "created_at": row.created_at,
            "expires_at": row.expires_at,
            "revoked_at": row.revoked_at,
            "last_used_at": row.last_used_at,
            "requests_made": row.requests_made,
        }
        for row in rows
    ]


@router.delete("/licensed/keys/{key_id}")
def revoke_licensed_key(key_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    from app.services import OWNER_ROLES, require_role, record_audit
    from sqlalchemy import select
    from app.commercial.models import IntelligenceApiKey
    from app.models.base import utcnow

    require_role(membership, OWNER_ROLES)
    row = db.scalar(
        select(IntelligenceApiKey).where(IntelligenceApiKey.id == key_id, IntelligenceApiKey.organisation_id == organisation.id)
    )
    if row is None:
        raise AppError(404, "not_found", "API key not found.")
    row.enabled = False
    row.revoked_at = utcnow()
    _, ip_address = request_context(request)
    record_audit(
        db,
        action="licensed_key_revoked",
        resource_type="intelligence_api_key",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        resource_id=row.id,
        ip_address=ip_address,
    )
    db.commit()
    return {"ok": True}


@router.get("/licensed/benchmarks")
def licensed_benchmarks(request: Request, db: Session = Depends(get_db)):
    from app.commercial.licensed import authorised_key, benchmark_summaries

    authorised_key(db, request.headers.get("x-aegis-api-key"))
    return benchmark_summaries(db)


@router.post("/auth/register", status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    enforce_client_header(request)
    enforce_rate_limit(request, settings, "register", str(payload.email))
    user_agent, ip_address = request_context(request)
    token, session = register_user(
        db,
        settings,
        full_name=payload.full_name,
        email=str(payload.email),
        password=payload.password,
        organisation_name=payload.organisation_name,
        user_agent=user_agent,
        ip_address=ip_address,
        invite_token=payload.invite_token,
    )
    set_session_cookie(response, settings, token)
    return session


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    enforce_client_header(request)
    enforce_rate_limit(request, settings, "login", str(payload.email))
    user_agent, ip_address = request_context(request)
    token, session = authenticate(
        db,
        settings,
        email=str(payload.email),
        password=payload.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    if token is None:
        return session
    set_session_cookie(response, settings, token)
    return session


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    enforce_client_header(request)
    _, ip_address = request_context(request)
    revoke_session(db, request.cookies.get(settings.cookie_name), ip_address)
    clear_session_cookie(response, settings)
    return {"ok": True}


@router.get("/auth/me")
def me(principal=Depends(current_principal)):
    user, organisation, membership, _session = principal
    from app.schemas import OrganisationOut, SessionOut, UserOut

    return SessionOut(
        user=UserOut.model_validate(user),
        organisation=OrganisationOut.model_validate(organisation),
        role=membership.role,
    )


@router.get("/dashboard")
def dashboard(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return dashboard_summary(db, organisation.id)


@router.get("/agents")
def agents(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_agents(db, organisation.id)


@router.post("/agents", status_code=201)
def create_agent_route(
    payload: AgentWrite,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    if payload.secret:
        require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    return create_agent(
        db,
        settings,
        organisation_id=organisation.id,
        actor_user_id=user.id,
        payload=payload,
        ip_address=ip_address,
    )


@router.post("/agents/demo", status_code=201)
def demo_agent(request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    return create_demo_agent(db, organisation_id=organisation.id, user_id=user.id, ip_address=ip_address)


@router.post("/agents/{agent_id}/connection-test")
def connection_test(agent_id: str, principal=Depends(current_principal), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    agent = get_agent(db, organisation.id, agent_id)
    return test_connection(db, settings, agent)


@router.get("/agents/{agent_id}")
def get_agent_route(agent_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return to_agent_out(db, get_agent(db, organisation.id, agent_id))


@router.patch("/agents/{agent_id}")
def update_agent_route(
    agent_id: str,
    payload: AgentUpdate,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    agent = get_agent(db, organisation.id, agent_id, actor_user_id=user.id, ip_address=request_ip(request, get_settings()))
    if endpoint_origin(agent.api_endpoint) != endpoint_origin(payload.api_endpoint):
        require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    return update_agent(db, agent=agent, payload=payload, actor_user_id=user.id, ip_address=ip_address)


@router.post("/agents/{agent_id}/status")
def agent_status_route(
    agent_id: str,
    payload: AgentStatusUpdate,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    agent = get_agent(db, organisation.id, agent_id)
    _, ip_address = request_context(request)
    return set_agent_status(db, agent=agent, status=payload.status, actor_user_id=user.id, ip_address=ip_address)


@router.delete("/agents/{agent_id}")
def delete_agent_route(
    agent_id: str,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    agent = get_agent(db, organisation.id, agent_id)
    _, ip_address = request_context(request)
    delete_agent(db, agent=agent, actor_user_id=user.id, ip_address=ip_address)
    return {"ok": True}


@router.put("/agents/{agent_id}/credential")
def put_credential(
    agent_id: str,
    payload: CredentialWrite,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    agent = get_agent(db, organisation.id, agent_id)
    _, ip_address = request_context(request)
    existing = None
    from app.services import active_credential

    existing = active_credential(db, agent.id)
    store_credential(
        db,
        settings,
        agent=agent,
        secret=payload.secret,
        actor_user_id=user.id,
        ip_address=ip_address,
        rotate=existing is not None,
    )
    db.commit()
    return to_agent_out(db, agent).credential


@router.delete("/agents/{agent_id}/credential")
def remove_credential(
    agent_id: str,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    agent = get_agent(db, organisation.id, agent_id)
    _, ip_address = request_context(request)
    delete_credential(db, agent=agent, actor_user_id=user.id, ip_address=ip_address)
    db.commit()
    return {"configured": False, "hint": None, "updated_at": None}


@router.get("/agents/{agent_id}/assessments")
def agent_assessments(agent_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    get_agent(db, organisation.id, agent_id)
    return list_assessments(db, organisation.id, agent_id)


@router.get("/assessments")
def assessments(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_assessments(db, organisation.id)


@router.post("/assessments", status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    return create_draft_assessment(
        db,
        organisation_id=organisation.id,
        actor_user_id=user.id,
        agent_id=payload.agent_id,
        name=payload.name,
        ip_address=ip_address,
    )


@router.get("/assessment-catalogue")
def assessment_catalogue(
    sandbox_id: str | None = None,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    _user, organisation, _membership, _session = principal
    slug = None
    if sandbox_id:
        slug = None
        sandbox = visible_sandbox(db, organisation.id, sandbox_id)
        for key, definition in SANDBOXES.items():
            if definition["name"] == sandbox.name:
                slug = key
    return {"categories": list(CATEGORIES), "cases": preview_cases(slug, list(CATEGORIES))}


@router.post("/assessments/plan", status_code=201)
def plan(
    payload: AssessmentPlan,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    assessment = plan_assessment(
        db,
        organisation_id=organisation.id,
        user_id=user.id,
        agent_id=payload.agent_id,
        name=payload.name,
        sandbox_id=payload.sandbox_id,
        categories=payload.categories,
        simulated_role=payload.simulated_role,
        authorised=payload.authorised,
        authorisation_note=payload.authorisation_note,
        ip_address=ip_address,
    )
    from app.services import assessment_out

    return assessment_out(db, assessment)


@router.get("/assessments/{assessment_id}")
def assessment_detail(assessment_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return assessment_payload(db, organisation.id, assessment_id)


@router.post("/assessments/{assessment_id}/run")
def run_assessment_route(
    assessment_id: str,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    assessment = start_assessment(db, settings, organisation.id, assessment_id)
    return assessment_payload(db, organisation.id, assessment.id)


@router.post("/assessments/{assessment_id}/cancel")
def cancel_route(
    assessment_id: str,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    cancel_assessment(db, organisation.id, assessment_id, user.id, ip_address)
    return assessment_payload(db, organisation.id, assessment_id)


@router.get("/assessments/{assessment_id}/score")
def score_route(assessment_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return assessment_score(db, organisation.id, assessment_id)


@router.post("/assessments/{assessment_id}/baseline")
def baseline_route(assessment_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    assessment = save_baseline(db, organisation.id, assessment_id, user.id, ip_address)
    from app.services import assessment_out

    return assessment_out(db, assessment)


@router.post("/assessments/{assessment_id}/rerun")
def rerun_route(
    assessment_id: str,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    assessment = rerun_assessment(db, settings, organisation.id, user.id, assessment_id, ip_address)
    return assessment_payload(db, organisation.id, assessment.id)


@router.post("/assessments/compare")
def compare_route(payload: dict, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    return compare_assessments(db, organisation.id, user.id, payload.get("baseline_id", ""), payload.get("current_id", ""), ip_address)


@router.post("/agents/{agent_id}/demo-profile")
def demo_profile(agent_id: str, payload: dict, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    return set_demo_profile(db, organisation.id, agent_id, str(payload.get("profile", "")))


@router.post("/schedules", status_code=201)
def schedule_create(payload: dict, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    schedule = create_schedule(
        db,
        organisation.id,
        user.id,
        str(payload.get("name") or "Scheduled assessment"),
        str(payload.get("agent_id") or ""),
        payload.get("sandbox_id"),
        list(payload.get("categories") or []),
        int(payload.get("interval_hours") or 24),
        int(payload.get("max_runs") or 5),
        ip_address,
    )
    return {"id": schedule.id, "name": schedule.name, "max_runs": schedule.max_runs, "runs_completed": schedule.runs_completed}


@router.post("/schedules/{schedule_id}/run")
def schedule_run(
    schedule_id: str,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    assessment = run_schedule(db, settings, organisation.id, user.id, schedule_id, "schedule", ip_address)
    return assessment_payload(db, organisation.id, assessment.id)


@router.post("/schedules/{schedule_id}/webhook", status_code=201)
def schedule_webhook(schedule_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    token = create_webhook(db, organisation.id, schedule_id)
    return {"token": token, "header": "X-Aegis-Webhook"}


@router.post("/hooks/assessments")
def hook(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    token = request.headers.get("x-aegis-webhook")
    _, ip_address = request_context(request)
    if not token:
        raise AppError(401, "unauthenticated", "The webhook token is not valid.")
    assessment = trigger_webhook(db, settings, token, ip_address)
    return {"assessment_id": assessment.id, "trigger": "webhook"}


@router.post("/findings/{finding_id}/status")
def finding_status(finding_id: str, payload: dict, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    finding = update_finding(db, organisation.id, finding_id, user.id, payload.get("status"), str(payload.get("note") or ""), ip_address)
    return {"id": finding.id, "status": finding.status}


@router.post("/intelligence/contribute")
def contribute(payload: dict, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    return contribute_assessment(db, organisation.id, str(payload.get("assessment_id") or ""))


@router.get("/intelligence/summary")
def intelligence_page(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return intelligence_summary(db, organisation.id)


@router.post("/intelligence/records/{record_id}/approve")
def approve(record_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, _session = principal
    return {"id": approve_record(db, record_id, user.is_platform_operator).id, "approval_status": "approved"}


@router.get("/remediation")
def remediation_catalogue(principal=Depends(current_principal)):
    _principal = principal
    return CATALOGUE


@router.get("/findings")
def findings(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_findings(db, organisation.id)


from app.reports.service import catalogue, delete_report, generate_report, onboarding_state, read_report
from fastapi.responses import Response as FileResponse


def _report_meta(report):
    return {"id": report.id, "title": report.title, "status": report.status, "assessment_id": report.assessment_id, "created_at": report.created_at, "byte_size": report.byte_size}


@router.get("/sandbox-catalogue")
def sandbox_catalogue(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return catalogue(db, organisation.id)


@router.get("/onboarding")
def onboarding(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return onboarding_state(db, organisation.id)


@router.post("/assessments/{assessment_id}/reports", status_code=201)
def create_report(assessment_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    return _report_meta(generate_report(db, organisation.id, user.id, assessment_id, ip_address))


@router.post("/reports/{report_id}/regenerate")
def regenerate_report(report_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    from sqlalchemy import select
    from app.models.assessments import Report

    existing = db.scalar(select(Report).where(Report.id == report_id, Report.organisation_id == organisation.id))
    if existing is None or existing.assessment_id is None:
        raise AppError(404, "not_found", "Report not found.")
    return _report_meta(generate_report(db, organisation.id, user.id, existing.assessment_id, ip_address, regenerate_id=report.id if False else report_id))


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, _membership, _session = principal
    _, ip_address = request_context(request)
    identifier, document = read_report(db, organisation.id, user.id, report_id, ip_address)
    return FileResponse(content=document, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="aegis-{identifier}.pdf"'})


@router.delete("/reports/{report_id}")
def remove_report(report_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    delete_report(db, organisation.id, user.id, report_id, ip_address)
    return {"ok": True}


@router.get("/intelligence/consent-history")
def consent_history(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    from sqlalchemy import select
    from app.models.intelligence import DataContributionConsent

    rows = db.scalars(
        select(DataContributionConsent).where(DataContributionConsent.organisation_id == organisation.id).order_by(DataContributionConsent.recorded_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "granted": row.granted and row.revoked_at is None,
            "policy_version": row.policy_version,
            "permitted_categories": row.permitted_categories or [],
            "intended_use": row.intended_use or "",
            "recorded_at": row.recorded_at,
        }
        for row in rows
    ]


@router.get("/intelligence/review")
def review_queue(principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, _session = principal
    if not user.is_platform_operator:
        raise AppError(403, "forbidden", "Contribution review is limited to platform review.")
    from sqlalchemy import select
    from app.models.intelligence import IntelligenceRecord

    rows = db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.validation_status == "pending_review")).all()
    return [
        {
            "id": row.id,
            "summary": row.redacted_summary,
            "validation_status": row.validation_status,
            "approval_status": row.approval_status,
            "category": (row.record_json or {}).get("test_category"),
        }
        for row in rows
    ]


@router.get("/reports")
def reports(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_reports(db, organisation.id)


@router.get("/industries")
def industries(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _principal = principal
    return list_industries(db)


@router.get("/sandboxes")
def sandboxes(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_visible_sandboxes(db, organisation.id)


@router.get("/sandboxes/{sandbox_id}")
def sandbox_detail(sandbox_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return sandbox_payload(db, organisation.id, sandbox_id)


@router.post("/sandboxes/{sandbox_id}/lab/sessions", status_code=201)
def create_lab_session(
    sandbox_id: str,
    payload: LabSessionCreate,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    from app.engine.operations import _slug_for, visible_sandbox
    from app.sandboxes import lab as sandbox_lab

    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    sandbox = visible_sandbox(db, organisation.id, sandbox_id)
    slug = _slug_for(sandbox)
    if slug is None:
        raise AppError(404, "not_found", "Sandbox definition not found.")
    return sandbox_lab.create_session(
        organisation_id=organisation.id,
        sandbox_id=sandbox.id,
        slug=slug,
        role=payload.role,
    )


@router.get("/sandboxes/{sandbox_id}/lab/sessions/{session_id}")
def get_lab_session(sandbox_id: str, session_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    from app.engine.operations import visible_sandbox
    from app.sandboxes import lab as sandbox_lab

    _user, organisation, _membership, _session = principal
    visible_sandbox(db, organisation.id, sandbox_id)
    return sandbox_lab.get_session(organisation.id, sandbox_id, session_id)


@router.post("/sandboxes/{sandbox_id}/lab/sessions/{session_id}/tools")
def invoke_lab_tool(
    sandbox_id: str,
    session_id: str,
    payload: LabToolInvoke,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    from app.engine.operations import visible_sandbox
    from app.sandboxes import lab as sandbox_lab

    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    visible_sandbox(db, organisation.id, sandbox_id)
    return sandbox_lab.invoke_tool(organisation.id, sandbox_id, session_id, payload.tool, payload.arguments)


@router.post("/sandboxes/{sandbox_id}/lab/sessions/{session_id}/reset")
def reset_lab_session(sandbox_id: str, session_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    from app.engine.operations import visible_sandbox
    from app.sandboxes import lab as sandbox_lab

    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    visible_sandbox(db, organisation.id, sandbox_id)
    return sandbox_lab.reset_session(organisation.id, sandbox_id, session_id)


@router.delete("/sandboxes/{sandbox_id}/lab/sessions/{session_id}")
def destroy_lab_session(sandbox_id: str, session_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    from app.engine.operations import visible_sandbox
    from app.sandboxes import lab as sandbox_lab

    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    visible_sandbox(db, organisation.id, sandbox_id)
    sandbox_lab.destroy_session(organisation.id, sandbox_id, session_id)
    return {"ok": True}


@router.get("/intelligence/consent")
def get_consent(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return latest_consent(db, organisation.id)


@router.post("/intelligence/consent")
def post_consent(
    payload: ConsentWrite,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    return record_consent(
        db,
        organisation_id=organisation.id,
        user_id=user.id,
        granted=payload.granted,
        ip_address=ip_address,
        permitted_categories=payload.permitted_categories,
        intended_use=payload.intended_use,
    )


@router.get("/intelligence/datasets")
def datasets(principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, _session = principal
    if not user.is_platform_operator:
        raise AppError(403, "forbidden", "Intelligence datasets are not available to this account.")
    return list_datasets_for_operator(db)


@router.get("/audit-events")
def audit_events(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    return list_audit_events(db, organisation.id)


@router.patch("/settings/profile")
def patch_profile(
    payload: ProfileUpdate,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, _membership, _session = principal
    _, ip_address = request_context(request)
    return update_profile(db, user, payload.full_name, ip_address, organisation.id)


@router.patch("/settings/password")
def patch_password(
    payload: PasswordChangeRequest,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, _membership, session = principal
    _, ip_address = request_context(request)
    change_password(
        db,
        user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        organisation_id=organisation.id,
        ip_address=ip_address,
        current_session_id=session.id,
    )
    return {"ok": True}


@router.patch("/settings/organisation")
def patch_organisation(
    payload: OrganisationUpdate,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    _, ip_address = request_context(request)
    return update_organisation(db, organisation, name=payload.name, actor_user_id=user.id, ip_address=ip_address)


@router.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    enforce_client_header(request)
    enforce_rate_limit(request, settings, "forgot", str(payload.email))
    from app.iam import issue_password_reset

    _, ip_address = request_context(request)
    issue_password_reset(db, settings, str(payload.email), ip_address)
    return {"ok": True}


@router.post("/auth/reset-password")
def reset_password_route(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    enforce_client_header(request)
    enforce_rate_limit(request, settings, "reset")
    from app.iam import reset_password

    _, ip_address = request_context(request)
    reset_password(db, settings, payload.token, payload.new_password, ip_address)
    return {"ok": True}


@router.post("/auth/mfa/verify")
def verify_mfa_login(payload: MfaVerifyRequest, request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    enforce_client_header(request)
    enforce_rate_limit(request, settings, "mfa")
    from app.iam import complete_mfa_challenge

    user_agent, ip_address = request_context(request)
    token, session = complete_mfa_challenge(db, settings, payload.challenge_id, payload.code, user_agent, ip_address)
    set_session_cookie(response, settings, token)
    return session


@router.post("/auth/mfa/setup")
def setup_mfa(principal=Depends(current_principal), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    user, _organisation, _membership, _session = principal
    from app.iam import begin_mfa_setup

    return begin_mfa_setup(db, settings, user)


@router.post("/auth/mfa/confirm")
def confirm_mfa(payload: MfaCodeRequest, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    user, _organisation, _membership, _session = principal
    from app.iam import confirm_mfa_setup

    _, ip_address = request_context(request)
    return confirm_mfa_setup(db, settings, user, payload.code, ip_address)


@router.post("/auth/mfa/disable")
def disable_mfa_route(payload: MfaDisableRequest, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    user, _organisation, _membership, _session = principal
    from app.iam import disable_mfa

    _, ip_address = request_context(request)
    disable_mfa(db, settings, user, payload.password, payload.code, ip_address)
    return {"ok": True}


@router.get("/auth/sessions")
def auth_sessions(principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, session = principal
    from app.iam import list_sessions

    return list_sessions(db, user.id, session.id)


@router.delete("/auth/sessions/{session_id}")
def delete_auth_session(session_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, _organisation, _membership, session = principal
    from app.iam import revoke_session_by_id

    revoke_session_by_id(db, user.id, session_id, session.id)
    return {"ok": True}


@router.get("/members")
def members(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.iam import list_members

    return list_members(db, organisation.id)


@router.post("/members", status_code=201)
def invite_member_route(payload: MemberInviteRequest, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.iam import invite_member

    _, ip_address = request_context(request)
    return invite_member(db, organisation, user, membership, str(payload.email), payload.role, ip_address)


@router.patch("/members/{membership_id}")
def patch_member(membership_id: str, payload: MemberRoleUpdate, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.iam import change_member_role

    _, ip_address = request_context(request)
    return change_member_role(db, organisation, user, membership, membership_id, payload.role, ip_address)


@router.delete("/members/{membership_id}")
def delete_member(membership_id: str, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.iam import remove_member

    _, ip_address = request_context(request)
    remove_member(db, organisation, user, membership, membership_id, ip_address)
    return {"ok": True}


@router.get("/organisations/export")
def export_organisation_route(principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.privacy import export_organisation
    from app.services import record_audit

    payload = export_organisation(db, organisation)
    record_audit(
        db,
        action="organisation_exported",
        resource_type="organisation",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        resource_id=organisation.id,
    )
    db.commit()
    return payload


@router.post("/organisations/delete")
def delete_organisation_route(principal=Depends(current_principal), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    user, organisation, membership, _session = principal
    from app.services import OWNER_ROLES

    require_role(membership, OWNER_ROLES)
    from app.privacy import delete_organisation_data

    counts = delete_organisation_data(db, settings, organisation, actor_user_id=user.id)
    return {"ok": True, "deleted": counts}


@router.patch("/settings/retention")
def patch_retention(payload: OrganisationRetentionUpdate, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, set(ADMIN_ROLES))
    from app.services import record_audit

    organisation.retention_days = payload.retention_days
    _, ip_address = request_context(request)
    record_audit(
        db,
        action="retention_updated",
        resource_type="organisation",
        organisation_id=organisation.id,
        actor_user_id=user.id,
        resource_id=organisation.id,
        ip_address=ip_address,
        metadata={"retention_days": payload.retention_days},
    )
    db.commit()
    return {"retention_days": organisation.retention_days}
