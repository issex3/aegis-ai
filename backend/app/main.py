import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import get_settings
from app.database import SessionLocal
from app.engine.seed import ensure_platform_content
from app.errors import register_exception_handlers
from app.hardening import RequestSizeLimitMiddleware, SecurityHeadersMiddleware, validate_production_settings
from app.models import Base  # noqa: F401
from app.scenarios.routes import router as scenario_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    session = SessionLocal()
    try:
        ensure_platform_content(session)
    finally:
        session.close()
    yield

settings = get_settings()
validate_production_settings(settings)
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logging.getLogger("aegis.security").setLevel(logging.INFO)

app = FastAPI(
    title="Aegis AI",
    version="0.2.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)
register_exception_handlers(app)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Aegis-Client", "X-Forwarded-For"],
)
app.include_router(router)
app.include_router(scenario_router)
