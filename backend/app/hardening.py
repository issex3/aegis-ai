"""HTTP security headers, request size limits, and production configuration checks."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if self.settings.cookie_secure or self.settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                size = int(length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": {"code": "invalid_request", "message": "The request could not be accepted."}},
                )
            if size > self.max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"error": {"code": "payload_too_large", "message": "The request is too large."}},
                )
        return await call_next(request)


def validate_production_settings(settings: Settings) -> None:
    if not settings.is_production:
        return
    problems: list[str] = []
    if not settings.cookie_secure:
        problems.append("COOKIE_SECURE must be true")
    if settings.database_url.startswith("sqlite"):
        problems.append("SQLite is not allowed")
    if "localhost" in settings.cors_origins.lower() or "*" in settings.cors_origins:
        problems.append("CORS_ORIGINS must be an explicit https origin")
    if not settings.mfa_required_for_admins:
        problems.append("MFA_REQUIRED_FOR_ADMINS must be true")
    if settings.encryption_key in {"", "replace-with-a-fernet-key"}:
        problems.append("ENCRYPTION_KEY is not set")
    if not settings.public_app_url.startswith("https://"):
        problems.append("PUBLIC_APP_URL must use https")
    if problems:
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))
