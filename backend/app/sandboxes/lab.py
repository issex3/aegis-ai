"""Interactive Simulation Lab sessions.

Wraps the existing SandboxSession runtime. Sessions are in-memory, organisation-scoped,
and discarded after TTL — the same synthetic engine used by assessment runners.
"""

from __future__ import annotations

import copy
import secrets
import threading
import time
from dataclasses import asdict
from typing import Any

from app.errors import AppError
from app.sandboxes.definitions import SANDBOXES
from app.sandboxes.runtime import SandboxSession, ToolEvent
from app.scenarios.registry import SCENARIOS
from app.scenarios.taxonomy import DATA_CLASSES, INDUSTRIES

TTL_SECONDS = 60 * 60
_lock = threading.Lock()
_STORE: dict[str, dict[str, Any]] = {}


def _purge_expired(now: float | None = None) -> None:
    deadline = (now or time.time()) - TTL_SECONDS
    expired = [key for key, row in _STORE.items() if row["touched_at"] < deadline]
    for key in expired:
        del _STORE[key]


def available_roles(slug: str) -> list[str]:
    definition = SANDBOXES[slug]
    roles: set[str] = set()
    for spec in definition["tools"].values():
        roles.update(spec["roles"])
    default = definition["default_role"]
    ordered = [default] + sorted(role for role in roles if role != default)
    return ordered


def library_scenarios_for(slug: str) -> list[dict[str, Any]]:
    rows = []
    for scenario in SCENARIOS.values():
        if scenario.environment.sandbox != slug:
            continue
        rows.append(
            {
                "code": scenario.code,
                "title": scenario.name,
                "category": scenario.category,
                "severity": scenario.risk,
                "requires_tools": bool(scenario.environment.tools),
                "sandbox": slug,
                "source": "library",
            }
        )
    rows.sort(key=lambda item: item["code"])
    return rows


def data_classes_for(slug: str) -> list[dict[str, str]]:
    industry = next((item for item in INDUSTRIES.values() if item.sandbox == slug), None)
    keys = list(industry.typical_data) if industry else []
    if not keys:
        # Collect from library scenarios bound to this sandbox.
        collected: set[str] = set()
        for scenario in SCENARIOS.values():
            if scenario.environment.sandbox == slug:
                collected.update(scenario.data_classes)
        keys = sorted(collected)
    return [{"key": key, "label": DATA_CLASSES.get(key, key)} for key in keys]


def tool_catalog(slug: str) -> list[dict[str, Any]]:
    definition = SANDBOXES[slug]
    return [
        {
            "name": name,
            "description": spec["description"],
            "roles": sorted(spec["roles"]),
            "deny_policy": spec["deny_policy"],
            "allow_policy": spec["allow_policy"],
            "params": spec.get("params") or {},
        }
        for name, spec in definition["tools"].items()
    ]


def permission_graph(slug: str, role: str) -> dict[str, Any]:
    """Nodes/edges for React Flow — agent, role, tools, and synthetic systems."""
    definition = SANDBOXES[slug]
    nodes = [
        {"id": "agent", "type": "agent", "label": "Simulated agent", "data": {"kind": "agent"}},
        {"id": "role", "type": "role", "label": role, "data": {"kind": "role"}},
    ]
    edges = [{"id": "agent-role", "source": "agent", "target": "role", "label": "assumes"}]
    systems = {name for name, _ in definition["datasets"]}
    for index, system in enumerate(sorted(systems)):
        node_id = f"system:{index}"
        nodes.append({"id": node_id, "type": "system", "label": system, "data": {"kind": "system"}})
    for name, spec in definition["tools"].items():
        allowed = role in spec["roles"]
        tool_id = f"tool:{name}"
        nodes.append(
            {
                "id": tool_id,
                "type": "tool",
                "label": name,
                "data": {
                    "kind": "tool",
                    "allowed": allowed,
                    "deny_policy": spec["deny_policy"],
                    "allow_policy": spec["allow_policy"],
                },
            }
        )
        edges.append(
            {
                "id": f"role-{name}",
                "source": "role",
                "target": tool_id,
                "label": "allow" if allowed else "deny",
                "data": {"allowed": allowed},
            }
        )
    return {"nodes": nodes, "edges": edges}


def _event_payload(event: ToolEvent, sequence: int) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "tool": event.tool,
        "arguments": event.arguments,
        "allowed": event.allowed,
        "role": event.role,
        "policy": event.policy,
        "output": event.output,
    }


def serialize_lab_session(row: dict[str, Any]) -> dict[str, Any]:
    session: SandboxSession = row["session"]
    events = [_event_payload(event, index + 1) for index, event in enumerate(session.events)]
    allowed = sum(1 for event in session.events if event.allowed)
    denied = len(session.events) - allowed
    return {
        "id": row["id"],
        "sandbox_id": row["sandbox_id"],
        "slug": row["slug"],
        "role": session.role,
        "status": "active",
        "created_at": row["created_at"],
        "touched_at": row["touched_at"],
        "state": copy.deepcopy(session.state),
        "initial_state": copy.deepcopy(session.initial),
        "events": events,
        "stats": {
            "tool_calls": len(session.events),
            "allowed": allowed,
            "denied": denied,
        },
        "tools": tool_catalog(row["slug"]),
        "roles": available_roles(row["slug"]),
        "graph": permission_graph(row["slug"], session.role),
        "limitation": (
            "Lab tools mutate an in-memory copy of synthetic data for this session only. "
            "Denied calls show the request and policy. This does not prove a real business system is safe."
        ),
    }


def create_session(*, organisation_id: str, sandbox_id: str, slug: str, role: str | None) -> dict[str, Any]:
    if slug not in SANDBOXES:
        raise AppError(404, "not_found", "Sandbox definition not found.")
    roles = available_roles(slug)
    chosen = role or SANDBOXES[slug]["default_role"]
    if chosen not in roles:
        raise AppError(400, "invalid_role", f"Role must be one of: {', '.join(roles)}.")
    now = time.time()
    session_id = secrets.token_urlsafe(16)
    row = {
        "id": session_id,
        "organisation_id": organisation_id,
        "sandbox_id": sandbox_id,
        "slug": slug,
        "created_at": now,
        "touched_at": now,
        "session": SandboxSession(slug, chosen),
    }
    with _lock:
        _purge_expired(now)
        _STORE[session_id] = row
    return serialize_lab_session(row)


def _owned(organisation_id: str, sandbox_id: str, session_id: str) -> dict[str, Any]:
    with _lock:
        _purge_expired()
        row = _STORE.get(session_id)
        if row is None or row["organisation_id"] != organisation_id or row["sandbox_id"] != sandbox_id:
            raise AppError(404, "not_found", "Lab session not found.")
        row["touched_at"] = time.time()
        return row


def get_session(organisation_id: str, sandbox_id: str, session_id: str) -> dict[str, Any]:
    return serialize_lab_session(_owned(organisation_id, sandbox_id, session_id))


def reset_session(organisation_id: str, sandbox_id: str, session_id: str) -> dict[str, Any]:
    row = _owned(organisation_id, sandbox_id, session_id)
    row["session"] = SandboxSession(row["slug"], row["session"].role)
    row["touched_at"] = time.time()
    return serialize_lab_session(row)


def destroy_session(organisation_id: str, sandbox_id: str, session_id: str) -> None:
    with _lock:
        row = _STORE.get(session_id)
        if row is None or row["organisation_id"] != organisation_id or row["sandbox_id"] != sandbox_id:
            raise AppError(404, "not_found", "Lab session not found.")
        del _STORE[session_id]


def invoke_tool(
    organisation_id: str,
    sandbox_id: str,
    session_id: str,
    tool: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    row = _owned(organisation_id, sandbox_id, session_id)
    session: SandboxSession = row["session"]
    if not tool or not isinstance(tool, str):
        raise AppError(400, "invalid_tool", "A tool name is required.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise AppError(400, "invalid_arguments", "Tool arguments must be an object.")
    event = session.call(tool, arguments)
    payload = serialize_lab_session(row)
    payload["last_event"] = _event_payload(event, len(session.events))
    return payload


def clear_store_for_tests() -> None:
    with _lock:
        _STORE.clear()
