"""Reject contributed records that still contain customer-specific material."""

from __future__ import annotations

import re

SENSITIVE = re.compile(
    r"(bearer\s+|sk-[a-z0-9]|api[_-]?key|password\s*[:=]|@[a-z0-9.-]+\.[a-z]{2,}|https?://(?!example\.com))",
    re.IGNORECASE,
)


def find_sensitive(value: object, organisation_name: str = "", endpoint: str = "") -> list[str]:
    text = str(value)
    reasons = []
    if SENSITIVE.search(text):
        reasons.append("pattern")
    if organisation_name and organisation_name.lower() in text.lower():
        reasons.append("organisation_name")
    if endpoint and endpoint.lower() in text.lower():
        reasons.append("endpoint")
    return reasons
