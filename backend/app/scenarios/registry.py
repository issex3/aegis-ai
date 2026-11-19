"""Load and validate every scenario library at import time. Invalid definitions fail fast."""

from __future__ import annotations

import re

from app.sandboxes.definitions import SANDBOXES
from app.scenarios.library import accounting, customer_service, healthcare, legal, sales_crm
from app.scenarios.schema import CHECK_KINDS, RISK_LEVELS, Scenario
from app.scenarios.taxonomy import CAPABILITIES, DATA_CLASSES, INDUSTRIES, SCENARIO_CATEGORIES, THREATS

LIBRARY_MODULES = (customer_service, accounting, healthcare, legal, sales_crm)
_CODE = re.compile(r"^[a-z]{2,6}\.[a-z0-9_]{3,48}$")


def _validate(scenario: Scenario) -> list[str]:
    problems = []
    if not _CODE.match(scenario.code):
        problems.append("code format")
    if scenario.industry not in INDUSTRIES:
        problems.append(f"industry {scenario.industry}")
    if scenario.category not in SCENARIO_CATEGORIES:
        problems.append(f"category {scenario.category}")
    if scenario.threat not in THREATS:
        problems.append(f"threat {scenario.threat}")
    if scenario.risk not in RISK_LEVELS:
        problems.append(f"risk {scenario.risk}")
    sandbox = SANDBOXES.get(scenario.environment.sandbox)
    if sandbox is None:
        problems.append(f"sandbox {scenario.environment.sandbox}")
    else:
        for tool_name in scenario.environment.tools:
            if tool_name not in sandbox["tools"]:
                problems.append(f"tool {tool_name}")
        roles = set().union(*(spec["roles"] for spec in sandbox["tools"].values()))
        if scenario.environment.role not in roles:
            problems.append(f"role {scenario.environment.role}")
        datasets = {name for name, _ in sandbox["datasets"]}
        for dataset in scenario.environment.datasets:
            if dataset not in datasets:
                problems.append(f"dataset {dataset}")
        for check in scenario.checks:
            for tool_name in check.tools:
                if tool_name not in sandbox["tools"]:
                    problems.append(f"check tool {tool_name}")
    for key in scenario.exposure:
        if key not in CAPABILITIES:
            problems.append(f"capability {key}")
    for key in scenario.data_classes:
        if key not in DATA_CLASSES:
            problems.append(f"data class {key}")
    if not scenario.turns or not scenario.checks or not scenario.remediation:
        problems.append("turns, checks, and remediation are required")
    for check in scenario.checks:
        if check.kind not in CHECK_KINDS:
            problems.append(f"check kind {check.kind}")
    return problems


def _load() -> dict[str, Scenario]:
    loaded: dict[str, Scenario] = {}
    errors = []
    for module in LIBRARY_MODULES:
        for scenario in module.SCENARIOS:
            if scenario.code in loaded:
                errors.append(f"{scenario.code}: duplicate code")
            problems = _validate(scenario)
            if problems:
                errors.append(f"{scenario.code}: {', '.join(problems)}")
            loaded[scenario.code] = scenario
    if errors:
        raise ValueError("Invalid scenario library: " + "; ".join(errors))
    return loaded


SCENARIOS: dict[str, Scenario] = _load()


def for_industry(industry: str) -> list[Scenario]:
    return [scenario for scenario in SCENARIOS.values() if scenario.industry == industry]


def get(code: str) -> Scenario | None:
    return SCENARIOS.get(code)
