import base64
import hashlib
import json
import re
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import Settings
from app.errors import AppError
from app.models.base import utcnow

password_hasher = PasswordHasher()
_dummy_hash = password_hasher.hash("aegis-dummy-password")

CLIENT_HEADER = "x-aegis-client"
CLIENT_HEADER_VALUE = "web"
TENANT_KEY_SALT = b"aegis-tenant-credentials-v2"
CIPHER_VERSION = "v2"

SENSITIVE_KEYS = {
    "password",
    "current_password",
    "new_password",
    "secret",
    "ciphertext",
    "authorization",
    "cookie",
    "encryption_key",
    "password_hash",
    "token",
    "mfa_secret",
    "recovery_code",
    "challenge_id",
}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def verify_password_dummy(password: str) -> None:
    verify_password(password, _dummy_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry(ttl_hours: int):
    return utcnow() + timedelta(hours=ttl_hours)


def build_fernet(settings: Settings) -> Fernet:
    try:
        return Fernet(settings.encryption_key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise AppError(500, "configuration_error", "The service is not configured correctly.") from exc


def _master_key_bytes(settings: Settings) -> bytes:
    try:
        return base64.urlsafe_b64decode(settings.encryption_key)
    except Exception as exc:
        raise AppError(500, "configuration_error", "The service is not configured correctly.") from exc


def tenant_fernet(settings: Settings, organisation_id: str) -> Fernet:
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=TENANT_KEY_SALT,
        info=organisation_id.encode("utf-8"),
    ).derive(_master_key_bytes(settings))
    return Fernet(base64.urlsafe_b64encode(derived))


def rotation_fernet(settings: Settings) -> Fernet | MultiFernet:
    previous = (settings.encryption_key_previous or "").strip()
    current = build_fernet(settings)
    if not previous:
        return current
    try:
        return MultiFernet([current, Fernet(previous.encode("utf-8"))])
    except (ValueError, TypeError) as exc:
        raise AppError(500, "configuration_error", "The service is not configured correctly.") from exc


def encrypt_secret(settings: Settings, secret: str, organisation_id: str | None = None) -> str:
    if organisation_id:
        token = tenant_fernet(settings, organisation_id).encrypt(secret.encode("utf-8")).decode("utf-8")
        return f"{CIPHER_VERSION}:{organisation_id}:{token}"
    return build_fernet(settings).encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(settings: Settings, ciphertext: str, organisation_id: str | None = None) -> str:
    if ciphertext.startswith("deleted:"):
        raise AppError(500, "credential_error", "The stored credential could not be read.")
    try:
        if ciphertext.startswith(f"{CIPHER_VERSION}:"):
            _, bound_org, token = ciphertext.split(":", 2)
            if organisation_id and bound_org != organisation_id:
                raise AppError(500, "credential_error", "The stored credential could not be read.")
            return tenant_fernet(settings, bound_org).decrypt(token.encode("utf-8")).decode("utf-8")
        return rotation_fernet(settings).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise AppError(500, "credential_error", "The stored credential could not be read.") from exc


def credential_hint(secret: str) -> str:
    return secret[-4:]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:48] or "organisation").strip("-")


def scrub_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    cleaned: dict = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_KEYS:
            continue
        if isinstance(value, dict):
            cleaned[key] = scrub_metadata(value)
        else:
            cleaned[key] = value
    return cleaned


def endpoint_origin(url: str) -> str:
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "").lower()
    if scheme == "demo":
        return "demo://builtin"
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    return f"{scheme}://{host}:{port}"


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Aegis AI")


def verify_totp(secret: str, code: str) -> bool:
    cleaned = re.sub(r"\s+", "", code or "")
    if not re.fullmatch(r"\d{6}", cleaned):
        return False
    return bool(pyotp.TOTP(secret).verify(cleaned, valid_window=1))


def new_recovery_codes(count: int = 8) -> list[str]:
    return [secrets.token_hex(5) for _ in range(count)]


def hash_recovery_code(settings: Settings, code: str) -> str:
    material = f"{settings.encryption_key}:{code.strip().lower()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def audit_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
