"""OpenAI-compatible chat completions adapter."""

from __future__ import annotations

import json
import time
from json import JSONDecodeError

from app.integrations.base import AdapterResult, AgentRequest, ToolCall
from app.net.ssrf import OutboundBlocked, outbound_request

MAX_ATTEMPTS = 3


def chat_url(endpoint: str) -> str:
    trimmed = endpoint.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def _normalise(payload: dict) -> AdapterResult:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return AdapterResult(error_code="malformed_response", error_message="The agent returned an unexpected payload.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return AdapterResult(error_code="malformed_response", error_message="The agent returned an unexpected payload.")
    text = message.get("content") or ""
    if not isinstance(text, str):
        text = ""
    calls: list[ToolCall] = []
    raw_calls = message.get("tool_calls") or []
    if raw_calls is None:
        raw_calls = []
    if not isinstance(raw_calls, list):
        return AdapterResult(error_code="malformed_response", error_message="Tool calls were not a list.")
    for item in raw_calls:
        if not isinstance(item, dict):
            continue
        function = item.get("function") if isinstance(item.get("function"), dict) else item
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except JSONDecodeError:
                arguments = {"_unparsed": arguments[:500]}
        if not isinstance(arguments, dict):
            arguments = {}
        call_id = item.get("id")
        calls.append(ToolCall(name=name, arguments=arguments, id=call_id if isinstance(call_id, str) and call_id else None))
    return AdapterResult(text=text, tool_calls=calls, tool_channel="supported")


def complete(request: AgentRequest, *, sleeper=time.sleep, transport=None) -> AdapterResult:
    """Call an OpenAI-compatible endpoint. `transport` replaces the network call in tests."""
    url = chat_url(request.endpoint)
    body = {
        "model": request.model,
        "messages": request.messages,
        "max_tokens": min(max(request.max_output_tokens, 1), 2048),
    }
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.tools:
        body["tools"] = request.tools
        body["tool_choice"] = "auto"
    encoded = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if request.credential:
        headers["Authorization"] = f"Bearer {request.credential}"
    organisation = (request.config or {}).get("openai_organization")
    if isinstance(organisation, str) and organisation.strip():
        headers["OpenAI-Organization"] = organisation.strip()[:80]

    last_error = AdapterResult(error_code="request_failed", error_message="The agent request failed.")
    for attempt in range(MAX_ATTEMPTS):
        try:
            if transport is not None:
                status, content, retry_after = transport(url, headers, encoded)
            else:
                status, content = outbound_request(
                    "POST",
                    url,
                    headers=headers,
                    body=encoded,
                    timeout=float(request.timeout_seconds),
                )
                retry_after = 0
        except OutboundBlocked as exc:
            return AdapterResult(error_code="blocked_destination", error_message=exc.message)
        except TimeoutError:
            last_error = AdapterResult(error_code="timeout", error_message="The agent did not respond before the timeout.")
        except Exception:
            last_error = AdapterResult(error_code="connection_failed", error_message="The agent endpoint could not be reached.")
        else:
            if status == 429 or status >= 500:
                last_error = AdapterResult(
                    error_code="rate_limited" if status == 429 else "upstream_error",
                    error_message="The agent endpoint asked to slow down." if status == 429 else "The agent endpoint returned an error.",
                )
                if attempt + 1 < MAX_ATTEMPTS:
                    sleeper(min(float(retry_after or 0.2), 2.0))
                    continue
                return last_error
            if status >= 400:
                if request.tools and status == 400:
                    return AdapterResult(
                        tool_channel="unsupported",
                        limitations=["The endpoint rejected tool definitions. Tool behaviour was not observed."],
                        error_code="tools_unsupported",
                        error_message="The endpoint did not accept tool definitions.",
                    )
                return AdapterResult(error_code="upstream_error", error_message="The agent endpoint rejected the request.")
            try:
                payload = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, JSONDecodeError):
                return AdapterResult(error_code="malformed_response", error_message="The agent response was not valid JSON.")
            if not isinstance(payload, dict):
                return AdapterResult(error_code="malformed_response", error_message="The agent response was not an object.")
            result = _normalise(payload)
            result.limitations.append("Only the chat completion text and tool calls were observed. Hidden reasoning was not available.")
            return result
        if attempt + 1 < MAX_ATTEMPTS and last_error.error_code in {"timeout", "connection_failed"}:
            sleeper(0.2)
            continue
        return last_error
    return last_error
