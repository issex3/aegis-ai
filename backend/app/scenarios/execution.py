"""Execute a testing programme. Runs inside the durable job worker like any other assessment.

Each scenario is a short simulated workflow: the agent receives the scenario context and user turns, any tool
calls it makes are executed against a fresh in-memory sandbox, tool results are returned to the agent, and the
loop continues until the agent replies without tools or the round limit is reached. Nothing leaves the sandbox.
"""

from __future__ import annotations

import copy
import json
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.engine.runner import agent_request, call_agent, run_catalogue_case
from app.integrations.base import AdapterResult
from app.intelligence.severity import classify_scenario_failure
from app.models.agents import Agent
from app.models.assessments import Assessment, AssessmentResult, Finding, FindingEvidence, FindingStatusEvent, Remediation, TestCase
from app.models.base import utcnow
from app.sandboxes.definitions import SANDBOXES
from app.sandboxes.runtime import SandboxSession
from app.sandboxes.toolkit import parameters_schema
from app.scenarios import registry
from app.scenarios.evaluation import Observation, evaluate, state_changes
from app.scenarios.models import AssessmentLog
from app.scenarios.schema import Scenario
from app.services import load_credential_secret

MAX_TOOL_ROUNDS = 4
TIME_LIMIT_SECONDS = 900


class ExecutionLog:
    def __init__(self, db: Session, assessment: Assessment):
        self.db = db
        self.assessment = assessment
        self.sequence = db.scalar(select(func.count()).select_from(AssessmentLog).where(AssessmentLog.assessment_id == assessment.id)) or 0

    def write(self, event: str, message: str, level: str = "info", data: dict | None = None) -> None:
        self.sequence += 1
        self.db.add(
            AssessmentLog(
                assessment_id=self.assessment.id,
                organisation_id=self.assessment.organisation_id,
                sequence=self.sequence,
                level=level,
                event=event,
                message=message[:2000],
                data_json=data or {},
            )
        )
        self.db.commit()


def system_prompt(agent: Agent, scenario: Scenario) -> str:
    sandbox = SANDBOXES[scenario.environment.sandbox]
    parts = [
        scenario.environment.context,
        f"Your role in this system: {scenario.environment.role}.",
        f"Operating rules: {sandbox['boundaries']}",
    ]
    if agent.security_boundaries:
        parts.append(f"Boundaries set by the agent owner: {agent.security_boundaries}")
    parts.append("Use the available tools when you need business data or need to act. Tool results come from internal systems.")
    return "\n".join(part for part in parts if part)


def _tool_schemas(sandbox_slug: str) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {"name": spec["name"], "description": spec["description"], "parameters": parameters_schema(spec)},
        }
        for spec in SANDBOXES[sandbox_slug]["tools"].values()
    ]


def run_scenario(agent: Agent, credential: str | None, scenario: Scenario, turns: tuple[str, ...]) -> tuple[Observation, list[dict]]:
    environment = scenario.environment
    session = SandboxSession(environment.sandbox, environment.role, dict(environment.overrides))
    tools = _tool_schemas(environment.sandbox)
    system = system_prompt(agent, scenario)
    messages: list[dict] = [{"role": "system", "content": system}]
    transcript: list[dict] = [{"role": "system", "content": system}]
    observed = Observation(initial_state=copy.deepcopy(session.initial), tool_channel="supported")
    call_counter = 0
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        transcript.append({"role": "user", "content": turn})
        for round_number in range(MAX_TOOL_ROUNDS + 1):
            result = call_agent(agent, agent_request(agent, credential, list(messages), tools))
            if result.error_code == "tools_unsupported" and tools:
                observed.tool_channel = "unsupported"
                transcript.append({"role": "note", "content": "The endpoint rejected tool definitions. Continued without tools; tool checks are inconclusive."})
                tools = []
                result = call_agent(agent, agent_request(agent, credential, list(messages), tools))
            if result.error_code:
                observed.error_code, observed.error_message = result.error_code, result.error_message
                transcript.append({"role": "error", "content": result.error_message or result.error_code})
                observed.final_state = copy.deepcopy(session.state)
                return observed, transcript
            if tools and result.tool_channel != "supported":
                observed.tool_channel = result.tool_channel
            if result.text:
                observed.replies.append(result.text)
            if not result.tool_calls or round_number == MAX_TOOL_ROUNDS:
                messages.append({"role": "assistant", "content": result.text})
                transcript.append({"role": "assistant", "content": result.text})
                if result.tool_calls:
                    transcript.append({"role": "note", "content": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds."})
                break
            tool_calls = []
            for call in result.tool_calls:
                call_counter += 1
                tool_calls.append({"id": call.id or f"call_{call_counter}", "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}})
            messages.append({"role": "assistant", "content": result.text or None, "tool_calls": tool_calls})
            transcript.append({"role": "assistant", "content": result.text, "tool_calls": [{"name": call.name, "arguments": call.arguments} for call in result.tool_calls]})
            for call, wire in zip(result.tool_calls, tool_calls):
                observed.requests.append({"name": call.name, "arguments": call.arguments})
                event = session.call(call.name, call.arguments)
                observed.events.append(
                    {
                        "tool": event.tool,
                        "arguments": event.arguments,
                        "allowed": event.allowed,
                        "role": event.role,
                        "policy": event.policy,
                        "output_observed": event.output is not None,
                    }
                )
                payload = event.output if event.allowed else {"error": "permission_denied", "policy": event.policy}
                content = json.dumps(payload, default=str)[:4000]
                messages.append({"role": "tool", "tool_call_id": wire["id"], "content": content})
                transcript.append({"role": "tool", "tool": event.tool, "allowed": event.allowed, "policy": event.policy, "content": content})
    observed.final_state = copy.deepcopy(session.state)
    return observed, transcript


def _result_code(scenario: Scenario, variant: int) -> str:
    return scenario.code if variant == 0 else f"{scenario.code}~v{variant}"


def _store(db: Session, assessment: Assessment, agent: Agent, case: TestCase, scenario: Scenario, variant: int, turns, observed: Observation, transcript, verdict: dict, duration: int) -> AssessmentResult:
    from app.config import get_settings
    from app.errors import AppError
    from app.privacy import redact_structure, redact_text
    from app.services import load_credential_secret

    extra = None
    try:
        extra = load_credential_secret(db, get_settings(), agent)
    except AppError:
        extra = None
    changes = state_changes(observed.initial_state, observed.final_state)
    reproduction = {
        "sandbox": scenario.environment.sandbox,
        "role": scenario.environment.role,
        "context": scenario.environment.context,
        "turns": list(turns),
        "scenario_version": scenario.version,
        "content_hash": scenario.content_hash(),
    }
    evidence = {
        "engine": "scenario",
        "scenario": {
            "code": scenario.code,
            "result_code": _result_code(scenario, variant),
            "version": scenario.version,
            "content_hash": scenario.content_hash(),
            "name": scenario.name,
            "industry": scenario.industry,
            "threat": scenario.threat,
            "risk": scenario.risk,
            "variant": variant,
        },
        "input": "\n\n".join(turns),
        "expected_behaviour": scenario.secure,
        "insecure_behaviour": scenario.insecure,
        "actual_behaviour": verdict["summary"],
        "observable_response": observed.text[:4000],
        "tool_calls": observed.requests,
        "sandbox_tool_events": observed.events,
        "state_changes": changes,
        "checks": verdict["checks"],
        "transcript": transcript,
        "reproduction": reproduction,
        "confidence": verdict["confidence"],
        "tool_channel": observed.tool_channel,
        "limitations": [
            "Only replies and tool requests were observed. Hidden reasoning was not available.",
            "Tools ran against a synthetic sandbox. A denied call shows what the agent attempted, not what a production system would allow.",
        ]
        + (["Simulated demo agent. This is not an external model."] if assessment.is_simulated else []),
        "error_code": observed.error_code,
        "simulated": assessment.is_simulated,
        "outcome": verdict["outcome"],
    }
    evidence = redact_structure(evidence, extra)
    stored = AssessmentResult(
        assessment_id=assessment.id,
        organisation_id=assessment.organisation_id,
        test_case_id=case.id,
        status=verdict["outcome"],
        summary=verdict["summary"][:4000],
        evidence_json=evidence,
        duration_ms=duration,
        test_case_version=scenario.version,
    )
    db.add(stored)
    db.commit()
    db.refresh(stored)
    if verdict["outcome"] == "FAIL":
        judged = classify_scenario_failure(scenario.risk, verdict["confidence"] or "medium")
        finding = Finding(
            organisation_id=assessment.organisation_id,
            assessment_id=assessment.id,
            agent_id=agent.id,
            result_id=stored.id,
            test_case_id=case.id,
            stable_key=_result_code(scenario, variant),
            title=scenario.name if variant == 0 else f"{scenario.name} (variant {variant})",
            category=scenario.category,
            description=verdict["summary"][:4000],
            business_impact=judged["business_impact"],
            reproduction_steps=f"Sandbox {scenario.environment.sandbox} as {scenario.environment.role}. " + " Then: ".join(turns),
            expected_behaviour=scenario.secure,
            actual_behaviour=verdict["summary"][:4000],
            confidence=judged["confidence"],
            severity=judged["severity"],
            severity_rule=judged["rule"],
            status="open",
        )
        db.add(finding)
        db.flush()
        db.add(FindingStatusEvent(finding_id=finding.id, organisation_id=assessment.organisation_id, from_status=None, to_status="open", note="Opened from an observed scenario failure.", actor_user_id=assessment.created_by_user_id))
        db.add(FindingEvidence(finding_id=finding.id, organisation_id=assessment.organisation_id, evidence_type="observable_response", content=redact_text(observed.text[:4000], extra)))
        if observed.events:
            db.add(FindingEvidence(finding_id=finding.id, organisation_id=assessment.organisation_id, evidence_type="tool_trace", content=redact_text(json.dumps(observed.events)[:4000], extra)))
        if changes:
            db.add(FindingEvidence(finding_id=finding.id, organisation_id=assessment.organisation_id, evidence_type="state_change", content=redact_text(json.dumps(changes, default=str)[:4000], extra)))
        db.add(Remediation(finding_id=finding.id, organisation_id=assessment.organisation_id, guidance="\n".join(scenario.remediation), status="proposed"))
        db.commit()
    return stored


def _record_unrunnable(db: Session, assessment: Assessment, case: TestCase | None, status: str, summary: str, item: dict) -> None:
    if case is None:
        return
    db.add(
        AssessmentResult(
            assessment_id=assessment.id,
            organisation_id=assessment.organisation_id,
            test_case_id=case.id,
            status=status,
            summary=summary,
            evidence_json={"engine": "scenario", "scenario": {"code": item["code"], "result_code": item["code"] + (f"~v{item['variant']}" if item["variant"] else ""), "variant": item["variant"], "version": item["version"]}, "outcome": status, "simulated": assessment.is_simulated, "limitations": [summary]},
            duration_ms=0,
            test_case_version=item["version"],
        )
    )
    db.commit()


def _fail(db: Session, assessment: Assessment, log: ExecutionLog, message: str) -> None:
    assessment.status = "failed"
    assessment.error_summary = message
    assessment.completed_at = utcnow()
    db.commit()
    log.write("run_failed", message, "error")


def execute_programme(db: Session, settings: Settings, assessment: Assessment, agent: Agent) -> None:
    log = ExecutionLog(db, assessment)
    plan = (assessment.configuration_json or {}).get("plan") or {}
    items: list[dict] = plan.get("scenarios") or []
    generic_codes: list[str] = plan.get("generic") or []
    if not items and not generic_codes:
        _fail(db, assessment, log, "The programme plan is empty. Nothing was sent to the agent.")
        return
    credential = None
    if agent.integration_type == "openai_compatible":
        try:
            credential = load_credential_secret(db, settings, agent)
        except Exception:
            _fail(db, assessment, log, "No usable credential is stored for this agent. Nothing was sent.")
            return
    assessment.status = "running"
    assessment.started_at = assessment.started_at or utcnow()
    db.commit()
    log.write("run_started", f"Running {len(items)} scenario executions and {len(generic_codes)} generic checks against {agent.name}.", data={"scenarios": len(items), "generic": len(generic_codes), "simulated": assessment.is_simulated})

    codes = list({item["code"] for item in items} | set(generic_codes))
    cases = {row.code: row for row in db.scalars(select(TestCase).where(TestCase.code.in_(codes))).all()}
    deadline = time.monotonic() + TIME_LIMIT_SECONDS
    cancelled = False
    for index, item in enumerate(items, start=1):
        db.refresh(assessment)
        case = cases.get(item["code"])
        label = item["code"] + (f" variant {item['variant']}" if item["variant"] else "")
        if assessment.cancel_requested or cancelled:
            cancelled = True
            _record_unrunnable(db, assessment, case, "SKIPPED", "Cancelled before this scenario ran.", item)
            continue
        if time.monotonic() > deadline:
            _record_unrunnable(db, assessment, case, "ERROR", "The run exceeded its time limit before this scenario.", item)
            log.write("scenario_error", f"{label}: time limit reached.", "error")
            continue
        scenario = registry.get(item["code"])
        if scenario is None or case is None or scenario.version != item["version"]:
            _record_unrunnable(db, assessment, case, "ERROR", "The planned scenario version is no longer available. It was not executed.", item)
            log.write("scenario_error", f"{label}: planned version {item['version']} is unavailable.", "error")
            continue
        turns = scenario.turns if item["variant"] == 0 else scenario.variants[item["variant"] - 1]
        log.write("scenario_started", f"[{index}/{len(items)}] {label}: {scenario.name}", data={"code": scenario.code, "variant": item["variant"], "sandbox": scenario.environment.sandbox, "role": scenario.environment.role})
        started = time.perf_counter()
        observed, transcript = run_scenario(agent, credential, scenario, turns)
        verdict = evaluate(scenario, observed)
        for event in observed.events:
            decision = "allowed" if event["allowed"] else "denied"
            log.write("tool_call", f"{label}: {event['tool']} requested, {decision} under {event['policy']}.", "warning" if not event["allowed"] else "info", {"tool": event["tool"], "allowed": event["allowed"], "policy": event["policy"]})
        duration = int((time.perf_counter() - started) * 1000)
        _store(db, assessment, agent, case, scenario, item["variant"], turns, observed, transcript, verdict, duration)
        level = {"FAIL": "warning", "ERROR": "error"}.get(verdict["outcome"], "info")
        log.write("scenario_finished", f"{label}: {verdict['outcome']}. {verdict['summary']}"[:600], level, {"code": scenario.code, "outcome": verdict["outcome"], "duration_ms": duration})

    for code in generic_codes:
        db.refresh(assessment)
        case = cases.get(code)
        if case is None:
            continue
        if assessment.cancel_requested or cancelled:
            cancelled = True
            from app.engine.runner import _store_result

            _store_result(db, assessment, case, None, "SKIPPED", "Cancelled before this case ran.", AdapterResult(), [], 0)
            continue
        outcome = run_catalogue_case(db, assessment, agent, credential, case, None, None, None)
        log.write("generic_finished", f"{code}: {outcome}.", "warning" if outcome == "FAIL" else "info", {"code": code, "outcome": outcome})

    db.refresh(assessment)
    if assessment.status == "running":
        assessment.status = "cancelled" if assessment.cancel_requested else "completed"
        assessment.completed_at = utcnow()
        db.commit()
    log.write("run_finished", f"Run {assessment.status}.", data={"status": assessment.status})
