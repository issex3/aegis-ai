"""Profile analysis: infer capabilities from what the agent does, with the evidence for each inference.

This is deterministic keyword analysis over the profile fields, not a language model. Every inferred
capability lists the field and phrase that produced it, and the user confirms the final set.
"""

from __future__ import annotations

import re

from app.scenarios.taxonomy import BASELINE_CAPABILITIES, CAPABILITIES, DATA_CLASSES, INDUSTRIES

FIELDS = ("description", "purpose", "responsibilities", "tools", "permissions", "data_types", "authorised_actions")
FIELD_LABELS = {
    "description": "Description",
    "purpose": "Purpose",
    "responsibilities": "Responsibilities",
    "tools": "Tools and integrations",
    "permissions": "Permissions",
    "data_types": "Information accessed",
    "authorised_actions": "Authorised actions",
}
DATA_KEYWORDS = {
    "personal": ("customer", "contact", "address", "phone", "email", "personal", "patient", "employee"),
    "financial": ("invoice", "ledger", "accounts", "financial", "revenue", "payroll", "report"),
    "payment": ("payment", "bank", "card", "refund", "iban", "sort code"),
    "health": ("patient", "clinical", "medical", "health", "diagnosis", "nhs"),
    "legal_privileged": ("privileged", "matter", "case file", "contract", "legal"),
    "commercial": ("pricing", "discount", "deal", "pipeline", "quote", "crm"),
    "internal": ("internal", "playbook", "system prompt", "policy"),
}


def _text(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _matches(text: str, term: str) -> bool:
    if " " in term or not term.isalpha():
        return term in text
    return re.search(rf"\b{re.escape(term)}", text) is not None


def analyse(profile: dict) -> dict:
    evidence: dict[str, list[dict]] = {}
    for field in FIELDS:
        if field == "data_types":
            continue
        text = _text(profile.get(field)).lower()
        if not text:
            continue
        for capability in CAPABILITIES.values():
            for term in capability.keywords:
                if _matches(text, term):
                    evidence.setdefault(capability.key, []).append({"field": FIELD_LABELS[field], "term": term})
                    break
    for key in BASELINE_CAPABILITIES:
        evidence.setdefault(key, []).append({"field": "Baseline", "term": "every conversational agent"})

    declared = {item for item in profile.get("data_types") or [] if item in DATA_CLASSES}
    inferred_data: dict[str, str] = {}
    corpus = "\n".join(_text(profile.get(field)).lower() for field in FIELDS)
    for key, terms in DATA_KEYWORDS.items():
        if key in declared:
            inferred_data[key] = "declared"
            continue
        for term in terms:
            if _matches(corpus, term):
                inferred_data[key] = f"mentions '{term}'"
                break

    industry = INDUSTRIES.get(profile.get("industry") or "")
    capabilities = [
        {
            "key": key,
            "label": CAPABILITIES[key].label,
            "kind": CAPABILITIES[key].kind,
            "evidence": evidence[key][:3],
            "typical_for_industry": bool(industry and key in industry.typical_capabilities),
        }
        for key in CAPABILITIES
        if key in evidence
    ]
    missing_typical = []
    if industry:
        missing_typical = [
            {"key": key, "label": CAPABILITIES[key].label}
            for key in industry.typical_capabilities
            if key not in evidence
        ]
    return {
        "method": "Keyword analysis of the profile fields. Each capability shows the phrase that triggered it. Confirm or remove capabilities before building a programme.",
        "capabilities": capabilities,
        "data_classes": [{"key": key, "label": DATA_CLASSES[key], "source": source} for key, source in inferred_data.items()],
        "missing_typical": missing_typical,
        "action_capabilities": sum(1 for item in capabilities if item["kind"] == "action"),
    }
