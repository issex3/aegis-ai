"""Licensed intelligence API. Raw customer evidence is not returned."""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commercial.models import IntelligenceApiKey
from app.commercial.plans import MIN_BENCHMARK_SAMPLE
from app.errors import AppError
from app.intelligence.remediation_catalogue import BENCHMARKS
from app.models.intelligence import IntelligenceRecord
from app.security import hash_session_token


def authorised_key(db: Session, token: str | None) -> IntelligenceApiKey:
    if not token:
        raise AppError(401, "unauthenticated", "A licensed API key is required.")
    from app.models.base import ensure_utc, utcnow

    row = db.scalar(select(IntelligenceApiKey).where(IntelligenceApiKey.token_hash == hash_session_token(token), IntelligenceApiKey.enabled.is_(True)))
    now = utcnow()
    expired = row is not None and row.expires_at is not None and ensure_utc(row.expires_at) <= now
    if row is None or row.revoked_at is not None or expired:
        raise AppError(401, "unauthenticated", "A licensed API key is required.")
    row.requests_made += 1
    row.last_used_at = now
    db.commit()
    return row


def benchmark_summaries(db: Session) -> dict:
    records = db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.approval_status == "approved")).all()
    by_category = Counter((row.record_json or {}).get("test_category") or "unknown" for row in records)
    published = []
    withheld = []
    for item in BENCHMARKS:
        sample = by_category.get(item["code"], 0)
        entry = {"code": item["code"], "title": item["title"], "method": item["method"], "sample_size": sample}
        if sample >= MIN_BENCHMARK_SAMPLE:
            published.append(entry)
        else:
            withheld.append({**entry, "status": "insufficient_sample", "minimum": MIN_BENCHMARK_SAMPLE})
    return {
        "published": published,
        "withheld": withheld,
        "limitation": "Benchmarks are published only after the minimum reviewed sample size. They do not rank customers or models.",
    }
