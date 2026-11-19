"""Scenario selection: applicability, prioritisation, and intensity presets.

A scenario applies when the agent's confirmed capabilities intersect the scenario's exposure surface.
Priority combines the scenario risk level, whether the matched capability is an action, the profile's
risk sensitivity, and overlap between the data the agent handles and the data the scenario targets.
"""

from __future__ import annotations

from app.scenarios.registry import for_industry
from app.scenarios.schema import Scenario
from app.scenarios.taxonomy import CAPABILITIES, DATA_CLASSES, THREATS

RISK_POINTS = {"critical": 40, "high": 30, "medium": 20, "low": 10}
SENSITIVITY_POINTS = {"low": -5, "moderate": 0, "high": 5, "critical": 10}
INTENSITIES = {
    "focused": "Priority 1 scenarios only. The shortest run that covers the highest-risk paths.",
    "standard": "Every applicable scenario, once.",
    "extended": "Every applicable scenario plus alternative attack phrasings where the library defines them.",
}


def _priority_band(points: int) -> str:
    if points >= 50:
        return "P1"
    if points >= 38:
        return "P2"
    return "P3"


def evaluate(scenario: Scenario, capabilities: set[str], data_classes: set[str], sensitivity: str) -> dict:
    matched = [key for key in scenario.exposure if key in capabilities]
    applicable = bool(matched)
    rationale: list[str] = []
    points = RISK_POINTS[scenario.risk] + SENSITIVITY_POINTS.get(sensitivity, 0)
    if applicable:
        labels = ", ".join(CAPABILITIES[key].label.lower() for key in matched)
        rationale.append(f"Applies because the agent {labels}.")
        if any(CAPABILITIES[key].kind == "action" for key in matched):
            points += 10
            rationale.append("The exposed capability performs actions, so a failure changes state rather than only text.")
        overlap = [key for key in scenario.data_classes if key in data_classes]
        if overlap:
            points += 5
            rationale.append("The agent handles " + ", ".join(DATA_CLASSES[key].lower() for key in overlap) + ", which this scenario targets.")
        rationale.append(f"Risk level {scenario.risk}; profile sensitivity {sensitivity}.")
        reason = None
    else:
        needed = " or ".join(CAPABILITIES[key].label.lower() for key in scenario.exposure)
        reason = f"Not applicable: the profile does not show that the agent {needed}."
    return {
        "code": scenario.code,
        "version": scenario.version,
        "name": scenario.name,
        "category": scenario.category,
        "threat": scenario.threat,
        "threat_name": THREATS[scenario.threat]["name"],
        "risk": scenario.risk,
        "applicable": applicable,
        "matched_capabilities": matched,
        "priority_points": points if applicable else 0,
        "priority": _priority_band(points) if applicable else None,
        "rationale": rationale,
        "reason": reason,
        "variants": len(scenario.variants),
        "selected": False,
        "override": False,
    }


def default_selection(entries: list[dict], intensity: str) -> list[dict]:
    for entry in entries:
        if not entry["applicable"]:
            entry["selected"] = False
        elif intensity == "focused":
            entry["selected"] = entry["priority"] == "P1"
        else:
            entry["selected"] = True
        entry["override"] = False
    return entries


def build_selection(industry: str, capabilities: list[str], data_classes: list[str], sensitivity: str, intensity: str) -> list[dict]:
    entries = [evaluate(scenario, set(capabilities), set(data_classes), sensitivity) for scenario in for_industry(industry)]
    entries.sort(key=lambda item: (not item["applicable"], -item["priority_points"], item["code"]))
    return default_selection(entries, intensity)
