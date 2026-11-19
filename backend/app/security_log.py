"""Structured security events, separate from ordinary application logs.

These records are written to the `aegis.security` logger as JSON. Production must
ship this stream to append-only storage; the application cannot make stdout immutable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("aegis.security")


def security_event(
    event: str,
    *,
    organisation_id: str | None = None,
    actor_user_id: str | None = None,
    ip_address: str | None = None,
    outcome: str = "recorded",
    **fields,
) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "outcome": outcome,
        "organisation_id": organisation_id,
        "actor_user_id": actor_user_id,
        "ip_address": ip_address,
    }
    for key, value in fields.items():
        if key in {"password", "secret", "token", "ciphertext", "authorization", "cookie"}:
            continue
        payload[key] = value
    logger.info("%s", json.dumps(payload, default=str, sort_keys=True))
