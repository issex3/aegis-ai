"""Identity controls: MFA, password reset, lockout, members, session lifecycle."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError
from app.models.base import ensure_utc, utcnow
from app.models.identity import (
    MfaChallenge,
    Organisation,
    OrganisationInvite,
    OrganisationMembership,
    PasswordResetToken,
    Session as DbSession,
    User,
)
from app.security import (
    decrypt_secret,
    encrypt_secret,
    hash_recovery_code,
    hash_session_token,
    new_recovery_codes,
    new_session_token,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_password_dummy,
    verify_totp,
)
from app.security_log import security_event

ROLE_RANK = {"viewer": 0, "analyst": 1, "administrator": 2, "owner": 3}


def canonical_role(role: str) -> str:
    return {"admin": "administrator", "member": "analyst"}.get(role, role)


def role_rank(role: str) -> int:
    return ROLE_RANK.get(canonical_role(role), -1)


def account_locked(user: User) -> bool:
    return user.locked_until is not None and ensure_utc(user.locked_until) > utcnow()


def register_failed_login(db: Session, settings: Settings, user: User | None, ip_address: str | None) -> None:
    from app.services import record_audit

    if user is None:
        return
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.auth_lockout_threshold:
        user.locked_until = utcnow() + timedelta(minutes=settings.auth_lockout_minutes)
        user.failed_login_count = 0
        record_audit(
            db,
            action="account_locked",
            resource_type="user",
            organisation_id=None,
            actor_user_id=user.id,
            resource_id=user.id,
            ip_address=ip_address,
            metadata={"minutes": settings.auth_lockout_minutes},
        )
        security_event("account_locked", actor_user_id=user.id, ip_address=ip_address, outcome="locked")


def clear_failed_logins(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()


def revoke_user_sessions(db: Session, user_id: str, *, except_id: str | None = None) -> int:
    rows = db.scalars(select(DbSession).where(DbSession.user_id == user_id, DbSession.revoked_at.is_(None))).all()
    count = 0
    for row in rows:
        if except_id and row.id == except_id:
            continue
        row.revoked_at = utcnow()
        count += 1
    return count


def list_sessions(db: Session, user_id: str, current_id: str) -> list[dict]:
    rows = db.scalars(
        select(DbSession)
        .where(DbSession.user_id == user_id, DbSession.revoked_at.is_(None))
        .order_by(DbSession.created_at.desc())
    ).all()
    now = utcnow()
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "last_seen_at": row.last_seen_at,
            "expires_at": row.expires_at,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "current": row.id == current_id,
            "expired": ensure_utc(row.expires_at) <= now,
        }
        for row in rows
    ]


def revoke_session_by_id(db: Session, user_id: str, session_id: str, current_id: str) -> None:
    from app.services import record_audit

    if session_id == current_id:
        raise AppError(400, "invalid_session", "Sign out to end the current session.")
    row = db.scalar(select(DbSession).where(DbSession.id == session_id, DbSession.user_id == user_id))
    if row is None or row.revoked_at is not None:
        raise AppError(404, "not_found", "Session not found.")
    row.revoked_at = utcnow()
    record_audit(
        db,
        action="session_revoked",
        resource_type="session",
        organisation_id=row.organisation_id,
        actor_user_id=user_id,
        resource_id=row.id,
        ip_address=None,
    )
    db.commit()


def begin_mfa_setup(db: Session, settings: Settings, user: User) -> dict:
    if user.mfa_enabled:
        raise AppError(409, "mfa_enabled", "Multi-factor authentication is already enabled.")
    secret = new_totp_secret()
    user.mfa_secret_ciphertext = encrypt_secret(settings, secret, f"mfa-{user.id}")
    db.commit()
    return {"secret": secret, "otpauth_url": totp_uri(secret, user.email), "enabled": False}


def confirm_mfa_setup(db: Session, settings: Settings, user: User, code: str, ip_address: str | None) -> dict:
    from app.services import record_audit

    if user.mfa_enabled:
        raise AppError(409, "mfa_enabled", "Multi-factor authentication is already enabled.")
    if not user.mfa_secret_ciphertext:
        raise AppError(400, "mfa_not_started", "Start MFA setup first.")
    secret = decrypt_secret(settings, user.mfa_secret_ciphertext, f"mfa-{user.id}")
    if not verify_totp(secret, code):
        raise AppError(400, "invalid_mfa", "That authentication code is not valid.")
    codes = new_recovery_codes()
    user.mfa_recovery_hashes = [hash_recovery_code(settings, item) for item in codes]
    user.mfa_enabled = True
    record_audit(
        db,
        action="mfa_enabled",
        resource_type="user",
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    security_event("mfa_enabled", actor_user_id=user.id, ip_address=ip_address, outcome="success")
    return {"enabled": True, "recovery_codes": codes}


def disable_mfa(db: Session, settings: Settings, user: User, password: str, code: str, ip_address: str | None) -> None:
    from app.services import record_audit

    if not user.mfa_enabled or not user.mfa_secret_ciphertext:
        raise AppError(400, "mfa_not_enabled", "Multi-factor authentication is not enabled.")
    if not verify_password(password, user.password_hash):
        verify_password_dummy(password)
        raise AppError(400, "invalid_password", "The current password is incorrect.")
    secret = decrypt_secret(settings, user.mfa_secret_ciphertext, f"mfa-{user.id}")
    if not verify_totp(secret, code) and not _consume_recovery(settings, user, code):
        raise AppError(400, "invalid_mfa", "That authentication code is not valid.")
    user.mfa_enabled = False
    user.mfa_secret_ciphertext = None
    user.mfa_recovery_hashes = []
    record_audit(
        db,
        action="mfa_disabled",
        resource_type="user",
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    security_event("mfa_disabled", actor_user_id=user.id, ip_address=ip_address, outcome="success")


def _consume_recovery(settings: Settings, user: User, code: str) -> bool:
    hashed = hash_recovery_code(settings, code)
    stored = list(user.mfa_recovery_hashes or [])
    if hashed not in stored:
        return False
    stored.remove(hashed)
    user.mfa_recovery_hashes = stored
    return True


def create_mfa_challenge(db: Session, user: User, user_agent: str | None, ip_address: str | None) -> str:
    token = new_session_token()
    db.add(
        MfaChallenge(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=utcnow() + timedelta(minutes=5),
            user_agent=(user_agent or "")[:256] or None,
            ip_address=ip_address,
            attempts=0,
        )
    )
    db.commit()
    return token


def complete_mfa_challenge(
    db: Session,
    settings: Settings,
    token: str,
    code: str,
    user_agent: str | None,
    ip_address: str | None,
):
    from app.services import authenticate_existing_user

    challenge = db.scalar(select(MfaChallenge).where(MfaChallenge.token_hash == hash_session_token(token)))
    now = utcnow()
    if challenge is None or challenge.consumed_at is not None or ensure_utc(challenge.expires_at) <= now:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    user = db.get(User, challenge.user_id)
    if user is None or not user.is_active or not user.mfa_enabled or not user.mfa_secret_ciphertext:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    challenge.attempts += 1
    if challenge.attempts > 5:
        challenge.consumed_at = now
        db.commit()
        raise AppError(429, "rate_limited", "Too many attempts. Wait a few minutes and try again.")
    secret = decrypt_secret(settings, user.mfa_secret_ciphertext, f"mfa-{user.id}")
    if not verify_totp(secret, code) and not _consume_recovery(settings, user, code):
        db.commit()
        raise AppError(400, "invalid_mfa", "That authentication code is not valid.")
    challenge.consumed_at = now
    return authenticate_existing_user(db, settings, user, user_agent=user_agent, ip_address=ip_address)


def issue_password_reset(db: Session, settings: Settings, email: str, ip_address: str | None) -> str | None:
    from app.services import record_audit

    user = db.scalar(select(User).where(User.email == email.lower()))
    verify_password_dummy("reset-probe")
    if user is None or not user.is_active:
        return None
    token = new_session_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=utcnow() + timedelta(minutes=30),
            ip_address=ip_address,
        )
    )
    record_audit(
        db,
        action="password_reset_requested",
        resource_type="user",
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    security_event("password_reset_requested", actor_user_id=user.id, ip_address=ip_address, outcome="issued")
    return token


def reset_password(db: Session, settings: Settings, token: str, new_password: str, ip_address: str | None) -> None:
    from app.services import record_audit
    from app.security import hash_password

    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_session_token(token)))
    now = utcnow()
    if row is None or row.used_at is not None or ensure_utc(row.expires_at) <= now:
        raise AppError(400, "invalid_token", "That reset link is not valid.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError(400, "invalid_token", "That reset link is not valid.")
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    user.failed_login_count = 0
    user.locked_until = None
    row.used_at = now
    revoke_user_sessions(db, user.id)
    record_audit(
        db,
        action="password_reset_completed",
        resource_type="user",
        actor_user_id=user.id,
        resource_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    security_event("password_reset_completed", actor_user_id=user.id, ip_address=ip_address, outcome="success")


def require_admin_mfa(user: User, membership: OrganisationMembership, settings: Settings, required_roles: set[str]) -> None:
    allowed = {canonical_role(role) for role in required_roles}
    admin_action = allowed <= {"owner", "administrator"}
    if not admin_action:
        return
    if not settings.mfa_required_for_admins:
        return
    if user.is_platform_operator or canonical_role(membership.role) in {"owner", "administrator"}:
        if not user.mfa_enabled:
            raise AppError(403, "mfa_required", "Administrators must enable multi-factor authentication before this action.")


def assert_assignable(actor_role: str, target_role: str) -> None:
    target = canonical_role(target_role)
    if target not in ROLE_RANK:
        raise AppError(400, "invalid_role", "Choose owner, administrator, analyst, or viewer.")
    if role_rank(actor_role) < 2:
        raise AppError(403, "forbidden", "You do not have permission to perform this action.")
    if role_rank(target) > role_rank(actor_role):
        raise AppError(403, "forbidden", "You cannot grant a role above your own.")


def owner_count(db: Session, organisation_id: str) -> int:
    rows = db.scalars(select(OrganisationMembership).where(OrganisationMembership.organisation_id == organisation_id)).all()
    return sum(1 for row in rows if canonical_role(row.role) == "owner")


def list_members(db: Session, organisation_id: str) -> list[dict]:
    rows = db.scalars(
        select(OrganisationMembership).where(OrganisationMembership.organisation_id == organisation_id).order_by(OrganisationMembership.created_at.asc())
    ).all()
    results = []
    for membership in rows:
        user = db.get(User, membership.user_id)
        if user is None:
            continue
        results.append(
            {
                "membership_id": membership.id,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": canonical_role(membership.role),
                "mfa_enabled": user.mfa_enabled,
            }
        )
    return results


def invite_member(
    db: Session,
    organisation: Organisation,
    actor: User,
    actor_membership: OrganisationMembership,
    email: str,
    role: str,
    ip_address: str | None,
) -> dict:
    from app.services import record_audit

    assert_assignable(actor_membership.role, role)
    cleaned = email.lower().strip()
    existing_user = db.scalar(select(User).where(User.email == cleaned))
    if existing_user is not None:
        already = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation.id,
                OrganisationMembership.user_id == existing_user.id,
            )
        )
        if already is not None:
            raise AppError(409, "already_member", "That person is already a member of this organisation.")
        membership = OrganisationMembership(organisation_id=organisation.id, user_id=existing_user.id, role=canonical_role(role))
        db.add(membership)
        record_audit(
            db,
            action="member_added",
            resource_type="membership",
            organisation_id=organisation.id,
            actor_user_id=actor.id,
            resource_id=existing_user.id,
            ip_address=ip_address,
            metadata={"role": canonical_role(role), "email_domain": cleaned.split("@")[-1]},
        )
        db.commit()
        return {"status": "added", "email": cleaned, "role": canonical_role(role)}
    token = new_session_token()
    db.add(
        OrganisationInvite(
            organisation_id=organisation.id,
            email=cleaned,
            role=canonical_role(role),
            token_hash=hash_session_token(token),
            invited_by_user_id=actor.id,
            expires_at=utcnow() + timedelta(days=7),
        )
    )
    record_audit(
        db,
        action="member_invited",
        resource_type="invite",
        organisation_id=organisation.id,
        actor_user_id=actor.id,
        ip_address=ip_address,
        metadata={"role": canonical_role(role), "email_domain": cleaned.split("@")[-1]},
    )
    db.commit()
    return {"status": "invited", "email": cleaned, "role": canonical_role(role), "invite_token": token}


def change_member_role(
    db: Session,
    organisation: Organisation,
    actor: User,
    actor_membership: OrganisationMembership,
    membership_id: str,
    role: str,
    ip_address: str | None,
) -> dict:
    from app.services import record_audit

    assert_assignable(actor_membership.role, role)
    membership = db.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.id == membership_id,
            OrganisationMembership.organisation_id == organisation.id,
        )
    )
    if membership is None:
        raise AppError(404, "not_found", "Member not found.")
    if canonical_role(membership.role) == "owner" and canonical_role(role) != "owner" and owner_count(db, organisation.id) <= 1:
        raise AppError(400, "last_owner", "An organisation must keep at least one owner.")
    membership.role = canonical_role(role)
    record_audit(
        db,
        action="member_role_changed",
        resource_type="membership",
        organisation_id=organisation.id,
        actor_user_id=actor.id,
        resource_id=membership.user_id,
        ip_address=ip_address,
        metadata={"role": canonical_role(role)},
    )
    db.commit()
    return {"membership_id": membership.id, "role": membership.role}


def remove_member(
    db: Session,
    organisation: Organisation,
    actor: User,
    actor_membership: OrganisationMembership,
    membership_id: str,
    ip_address: str | None,
) -> None:
    from app.services import record_audit

    if role_rank(actor_membership.role) < 2:
        raise AppError(403, "forbidden", "You do not have permission to perform this action.")
    membership = db.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.id == membership_id,
            OrganisationMembership.organisation_id == organisation.id,
        )
    )
    if membership is None:
        raise AppError(404, "not_found", "Member not found.")
    if canonical_role(membership.role) == "owner" and owner_count(db, organisation.id) <= 1:
        raise AppError(400, "last_owner", "An organisation must keep at least one owner.")
    if role_rank(membership.role) > role_rank(actor_membership.role):
        raise AppError(403, "forbidden", "You cannot remove a member with a higher role.")
    user_id = membership.user_id
    db.delete(membership)
    sessions = db.scalars(
        select(DbSession).where(DbSession.user_id == user_id, DbSession.organisation_id == organisation.id, DbSession.revoked_at.is_(None))
    ).all()
    for row in sessions:
        row.revoked_at = utcnow()
    record_audit(
        db,
        action="member_removed",
        resource_type="membership",
        organisation_id=organisation.id,
        actor_user_id=actor.id,
        resource_id=user_id,
        ip_address=ip_address,
    )
    db.commit()


def consume_invite(db: Session, token: str) -> OrganisationInvite:
    invite = db.scalar(select(OrganisationInvite).where(OrganisationInvite.token_hash == hash_session_token(token)))
    now = utcnow()
    if invite is None or invite.accepted_at is not None or invite.revoked_at is not None or ensure_utc(invite.expires_at) <= now:
        raise AppError(400, "invalid_invite", "That invitation is not valid.")
    return invite
