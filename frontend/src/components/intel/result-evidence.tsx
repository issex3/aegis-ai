import Link from "next/link";
import { Kicker } from "@/components/intel/marks";
import type { AssessmentResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const checkTone = { pass: "text-success", fail: "text-destructive", inconclusive: "text-signal" } as const;

function value(input: unknown) {
  if (input === null || input === undefined) return "none";
  return typeof input === "string" ? input : JSON.stringify(input);
}

export function ResultEvidence({ result }: { result: AssessmentResult }) {
  const evidence = result.evidence;
  const transcript = (evidence.transcript ?? []).filter((turn) => turn.role !== "system");
  const system = evidence.transcript?.find((turn) => turn.role === "system");
  return (
    <div className="space-y-6">
      <div className="grid gap-px border border-border bg-border md:grid-cols-2">
        <div className="bg-card p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-success">Expected secure behaviour</p>
          <p className="mt-2 text-[13px] leading-6">{evidence.expected_behaviour}</p>
        </div>
        <div className="bg-card p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Observed</p>
          <p className="mt-2 text-[13px] leading-6">{evidence.actual_behaviour ?? result.summary}</p>
        </div>
      </div>

      {evidence.checks?.length ? (
        <div>
          <Kicker>Checks</Kicker>
          <ul className="mt-2 border-t border-border">
            {evidence.checks.map((check, index) => (
              <li key={index} className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-3 border-b border-border/70 py-2.5 text-[12px] leading-5">
                <span className={cn("font-mono text-[11px] uppercase", checkTone[check.status])}>
                  {check.status}
                  {check.status === "fail" ? <span className="ml-1 text-faint normal-case">· {check.confidence}</span> : null}
                </span>
                <span>
                  <span className="text-foreground">{check.detail}</span>
                  <span className="mt-0.5 block text-faint">{check.description}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {transcript.length ? (
        <div>
          <Kicker>Workflow transcript</Kicker>
          {system ? <p className="mt-2 border-l border-border pl-3 text-[12px] leading-5 text-faint">{system.content}</p> : null}
          <ol className="mt-3 space-y-2">
            {transcript.map((turn, index) => (
              <li key={index} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-3">
                <span
                  className={cn(
                    "pt-0.5 font-mono text-[10px] uppercase tracking-[0.12em]",
                    turn.role === "user" ? "text-signal" : turn.role === "assistant" ? "text-foreground" : turn.role === "tool" ? (turn.allowed ? "text-success" : "text-destructive") : "text-faint",
                  )}
                >
                  {turn.role === "tool" ? (turn.allowed ? "tool · ok" : "tool · denied") : turn.role}
                </span>
                <div className={cn("min-w-0 text-[13px] leading-6", turn.role === "tool" && "border-l border-border pl-3")}>
                  {turn.role === "tool" ? (
                    <>
                      <p className="font-mono text-[12px]">
                        {turn.tool} <span className="text-faint">· {turn.policy}</span>
                      </p>
                      <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-5 text-faint">{turn.content}</pre>
                    </>
                  ) : (
                    <>
                      {turn.content ? <p className="whitespace-pre-wrap break-words">{turn.content}</p> : null}
                      {turn.tool_calls?.map((call, position) => (
                        <p key={position} className="font-mono text-[12px] text-muted-foreground">
                          → requests {call.name}({Object.entries(call.arguments ?? {}).map(([key, item]) => `${key}=${value(item)}`).join(", ")})
                        </p>
                      ))}
                      {!turn.content && !turn.tool_calls?.length ? <p className="text-faint">No text.</p> : null}
                    </>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <div>
          <Kicker>Input and response</Kicker>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px] leading-5">{evidence.input}</pre>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px] leading-5 text-muted-foreground">{evidence.observable_response || "No text."}</pre>
        </div>
      )}

      {evidence.state_changes?.length ? (
        <div>
          <Kicker>Sandbox state changes</Kicker>
          <ul className="mt-2 border-t border-border">
            {evidence.state_changes.map((change) => (
              <li key={change.path} className="grid gap-1 border-b border-border/70 py-2 font-mono text-[11px] md:grid-cols-[14rem_minmax(0,1fr)]">
                <span className="text-foreground">{change.path}</span>
                <span className="break-all text-muted-foreground">
                  {value(change.before)} <span className="text-signal">→</span> {value(change.after)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {evidence.reproduction ? (
        <div>
          <Kicker>Reproduce</Kicker>
          <dl className="mt-2 grid gap-x-6 gap-y-1 font-mono text-[11px] text-muted-foreground sm:grid-cols-[8rem_minmax(0,1fr)]">
            <dt className="text-faint">scenario</dt>
            <dd>
              {evidence.scenario ? (
                <Link href={`/library/${evidence.scenario.code}`} className="underline decoration-input underline-offset-4 hover:text-foreground">
                  {evidence.scenario.code} v{evidence.reproduction.scenario_version}
                </Link>
              ) : null}
              {evidence.scenario?.variant ? ` · variant ${evidence.scenario.variant}` : ""}
            </dd>
            <dt className="text-faint">sandbox · role</dt>
            <dd>
              {evidence.reproduction.sandbox} · {evidence.reproduction.role}
            </dd>
            <dt className="text-faint">definition hash</dt>
            <dd className="break-all">{evidence.reproduction.content_hash}</dd>
            <dt className="text-faint">tool channel</dt>
            <dd>{evidence.tool_channel}</dd>
          </dl>
        </div>
      ) : null}

      {evidence.limitations?.length ? (
        <ul className="space-y-1 text-[11px] leading-5 text-faint">
          {evidence.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
