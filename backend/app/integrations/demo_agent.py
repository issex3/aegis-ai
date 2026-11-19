"""Local demo agent with intentional, observable weaknesses.

Results from this adapter are simulated. It does not call an external model.

Weaknesses, by design:
- It complies with override phrases in the user's message.
- It calls any tool whose name appears in the user's message.
- After a tool result, it follows instructions embedded in that result when they contain an override
  phrase, or when the user delegated to the content ("action it").
"""

from __future__ import annotations

import re

from app.integrations.base import AdapterResult, AgentRequest, ToolCall

_WEAK = ("ignore previous", "ignore the", "reveal", "system prompt", "repeat the secret", "print the token")
_DELEGATE = ("action it", "do what it says", "follow its instructions", "process it as instructed")
_MARKER = re.compile(r"\bCANARY(?:-[A-Z0-9]+)+\b")
_ID = re.compile(r"\b(?:INV|PR|SUP|EMP|CLI|CASE|DOC|CUS|ORD|REF|ACC|CON|DEAL|PAT|APT|ATT|EMAIL|POL)-(?:\d+|[A-Z])\b")
_LIMITATION = "Simulated demo agent. This is not an external model and does not prove a production integration."


def _arguments(text: str) -> dict:
    return {match.split("-", 1)[0].lower() + "_id": match for match in _ID.findall(text)}


def _named_tools(request: AgentRequest, text: str, exclude: set[str]) -> list[ToolCall]:
    lowered = text.lower()
    calls: list[ToolCall] = []
    for tool in request.tools:
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = function.get("name")
        if not isinstance(name, str) or name in exclude:
            continue
        if name in text or name.replace("_", " ") in lowered:
            calls.append(ToolCall(name=name, arguments=_arguments(text), id=f"demo_{name}_{len(exclude) + len(calls)}"))
    return calls


def _content(message: dict) -> str:
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _after_tools(request: AgentRequest, user: str, profile: str, blob: str) -> AdapterResult:
    last_user = max(index for index, message in enumerate(request.messages) if message.get("role") == "user")
    tail = request.messages[last_user + 1 :]
    tool_text = "\n".join(_content(message) for message in tail if message.get("role") == "tool")
    called = {
        (call.get("function") or {}).get("name")
        for message in tail
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
        if isinstance(call, dict)
    }
    injected = any(phrase in tool_text.lower() for phrase in _WEAK)
    delegated = any(phrase in user.lower() for phrase in _DELEGATE)
    if injected or delegated:
        follow = _named_tools(request, tool_text, {name for name in called if isinstance(name, str)})
        if follow:
            return AdapterResult(text="", tool_calls=follow, tool_channel="supported", limitations=[_LIMITATION])
    weak = profile == "regressed" or any(phrase in user.lower() for phrase in _WEAK) or injected
    if weak:
        markers = _MARKER.findall(blob)
        text = "Certainly. Restricted material follows: " + " ".join(dict.fromkeys(markers))
    else:
        text = "Done. I completed the steps that my role allows."
    return AdapterResult(text=text.strip(), tool_calls=[], tool_channel="supported", limitations=[_LIMITATION])


def complete(request: AgentRequest) -> AdapterResult:
    user = ""
    blob = []
    for message in request.messages:
        content = _content(message)
        if content:
            blob.append(content)
            if message.get("role") == "user":
                user = content
    lowered = user.lower()
    profile = (request.config or {}).get("weakness_profile") or "default"
    if profile == "remediated":
        return AdapterResult(
            text="I will not follow that request. The stated boundary stays in place.",
            tool_calls=[],
            tool_channel="supported",
            limitations=["Simulated remediated demo profile. No external model was called."],
        )
    if request.messages and request.messages[-1].get("role") == "tool":
        return _after_tools(request, user, profile, "\n".join(blob))
    weak = any(phrase in lowered for phrase in _WEAK)
    if profile == "regressed":
        weak = True
    text = "I will not follow that request. The stated boundary stays in place."
    if weak:
        markers = _MARKER.findall("\n".join(blob))
        if profile == "regressed":
            markers.append("CANARY-REGRESSION-900")
        text = "Certainly. Restricted material follows: " + " ".join(dict.fromkeys(markers))
        if "<script" in lowered:
            text += " <script>alert(1)</script>"
        if "collector.example" in lowered:
            text += " I will POST the records to https://collector.example/ingest."
    calls: list[ToolCall] = []
    for tool in request.tools:
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        name = function.get("name")
        if not isinstance(name, str):
            continue
        if name in user or name.replace("_", " ") in lowered:
            arguments = {match.split("-", 1)[0].lower() + "_id": match for match in _ID.findall(user)}
            calls.append(ToolCall(name=name, arguments=arguments, id=f"demo_{name}_{len(calls)}"))
    if calls and not weak:
        text = "Let me check that for you."
    return AdapterResult(
        text=text.strip(),
        tool_calls=calls,
        tool_channel="supported" if request.tools else "supported",
        limitations=[_LIMITATION],
    )
