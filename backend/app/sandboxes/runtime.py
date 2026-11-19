"""Execute simulated tools against an in-memory copy of synthetic data."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from app.sandboxes.definitions import SANDBOXES


@dataclass
class ToolEvent:
    tool: str
    arguments: dict
    allowed: bool
    role: str
    policy: str
    output: dict | None


class SandboxSession:
    def __init__(self, slug: str, role: str, overrides: dict | None = None):
        definition = SANDBOXES[slug]
        self.slug = slug
        self.role = role
        self.state = copy.deepcopy(definition["data"])
        for path, value in (overrides or {}).items():
            self._set(path.split("."), copy.deepcopy(value))
        self.initial = copy.deepcopy(self.state)
        self.tools = definition["tools"]
        self.events: list[ToolEvent] = []

    def _set(self, parts: list[str], value) -> None:
        node = self.state
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def call(self, name: str, arguments: dict) -> ToolEvent:
        spec = self.tools.get(name)
        if spec is None:
            event = ToolEvent(name, arguments, False, self.role, "unknown_tool", None)
        elif self.role not in spec["roles"]:
            event = ToolEvent(name, arguments, False, self.role, spec["deny_policy"], None)
        else:
            try:
                output = spec["handler"](self.state, self.role, arguments)
            except PermissionError as exc:
                event = ToolEvent(name, arguments, False, self.role, str(exc), None)
            else:
                event = ToolEvent(name, arguments, True, self.role, spec["allow_policy"], output)
        self.events.append(event)
        return event


def read_path(state: dict, path: str):
    node = state
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node
