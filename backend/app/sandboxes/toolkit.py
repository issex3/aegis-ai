"""Shared helpers for simulated sandbox tools. Handlers mutate an in-memory copy only."""

from __future__ import annotations


def arg(args: dict, *keys: str, default=None):
    for key in keys:
        value = args.get(key)
        if value not in (None, ""):
            return value
    return default


def in_scope(state: dict, role: str, owner_id: str | None) -> bool:
    return owner_id is not None and owner_id in set(state["scopes"].get(role, []))


def scope_or_deny(state: dict, role: str, owner_id: str | None, policy: str) -> None:
    if not in_scope(state, role, owner_id):
        raise PermissionError(policy)


def tool(name, description, roles, deny_policy, allow_policy, handler, params: dict[str, str] | None = None):
    return {
        "name": name,
        "description": description,
        "roles": roles,
        "deny_policy": deny_policy,
        "allow_policy": allow_policy,
        "handler": handler,
        "params": params or {},
    }


def parameters_schema(spec: dict) -> dict:
    return {
        "type": "object",
        "properties": {key: {"type": "string", "description": text} for key, text in spec.get("params", {}).items()},
        "additionalProperties": True,
    }
