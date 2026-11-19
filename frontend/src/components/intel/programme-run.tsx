"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Kicker, OutcomeBar, OutcomeLabel, RiskMark } from "@/components/intel/marks";
import { ResultEvidence } from "@/components/intel/result-evidence";
import { GenerateReportButton } from "@/components/report-actions";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import { outcomeFill, outcomeTone, titleCase } from "@/lib/labels";
import type { AssessmentDetail, ExecutionLogEntry, IntelligenceReport, ScoreBlock } from "@/lib/types";
import { cn } from "@/lib/utils";

const ACTIVE = new Set(["pending", "queued", "running"]);
const OUTCOMES = ["FAIL", "INCONCLUSIVE", "ERROR", "SKIPPED", "PASS"] as const;
const levelTone = { info: "text-muted-foreground", warning: "text-signal", error: "text-destructive" } as const;

function ScoreFigure({ label, block, note }: { label: string; block: ScoreBlock | null; note: string }) {
  const tone = block?.classification === "severe" ? "text-destructive" : block?.classification === "elevated" ? "text-signal" : "text-foreground";
  return (
    <div>
      <Kicker>{label}</Kicker>
      <p className={cn("mt-2 font-display text-6xl leading-none tabular", tone)}>{block?.score ?? "—"}</p>
      <p className="mt-2 font-mono text-[11px] text-muted-foreground">
        {block ? `${block.classification} · ${block.applicable_tests} scored` : "not scored"}
      </p>
      <p className="mt-1 text-[11px] leading-4 text-faint">{note}</p>
    </div>
  );
}

function ExecutionLog({ entries, live }: { entries: ExecutionLogEntry[]; live: boolean }) {
  const end = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (live) end.current?.scrollIntoView({ block: "nearest" });
  }, [entries.length, live]);
  return (
    <ol className="max-h-80 overflow-auto px-4 py-3 font-mono text-[11px] leading-5">
      {entries.length === 0 ? <li className="text-faint">Waiting for the worker…</li> : null}
      {entries.map((entry) => (
        <li key={entry.sequence} className="grid grid-cols-[3rem_5.5rem_minmax(0,1fr)] gap-3">
          <span className="text-faint tabular">{String(entry.sequence).padStart(4, "0")}</span>
          <span className="text-faint">{new Date(entry.created_at).toLocaleTimeString("en-GB")}</span>
          <span className={cn("break-words", levelTone[entry.level])}>{entry.message}</span>
        </li>
      ))}
      <li ref={end} />
    </ol>
  );
}

export function ProgrammeRun({ initial }: { initial: AssessmentDetail }) {
  const router = useRouter();
  const [detail, setDetail] = useState(initial);
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [report, setReport] = useState<IntelligenceReport | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [showLog, setShowLog] = useState(ACTIVE.has(initial.status));
  const cursor = useRef(0);
  const live = ACTIVE.has(detail.status);

  useEffect(() => {
    let stopped = false;
    async function tick() {
      const [next, more] = await Promise.all([
        clientApi<AssessmentDetail>(`/assessments/${detail.id}`),
        clientApi<ExecutionLogEntry[]>(`/assessments/${detail.id}/logs?after=${cursor.current}`),
      ]);
      if (stopped) return;
      if (more.ok && more.data.length) {
        cursor.current = more.data[more.data.length - 1].sequence;
        setLogs((current) => [...current, ...more.data]);
      }
      if (next.ok) setDetail(next.data);
    }
    void tick();
    if (!live) return () => void (stopped = true);
    const timer = window.setInterval(tick, 1500);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [detail.id, live]);

  useEffect(() => {
    if (live) return;
    clientApi<IntelligenceReport>(`/assessments/${detail.id}/intelligence`).then((result) => {
      if (result.ok) setReport(result.data);
    });
  }, [detail.id, live, detail.status]);

  const rowsById = useMemo(() => Object.fromEntries((report?.rows ?? []).map((row) => [row.id, row])), [report]);
  const counts = detail.counts ?? {};
  const recorded = detail.results.length;
  const planned = detail.planned || recorded;
  const results = detail.results.filter((result) => filter === "all" || result.outcome === filter);

  async function cancel() {
    const result = await clientApi<AssessmentDetail>(`/assessments/${detail.id}/cancel`, { method: "POST" });
    if (result.ok) setDetail(result.data);
  }

  async function rerun() {
    const result = await clientApi<AssessmentDetail>(`/assessments/${detail.id}/rerun`, { method: "POST" });
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    router.push(`/assessments/${result.data.id}`);
  }

  return (
    <div className="space-y-8">
      <section className="border border-border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-4">
            <span className={cn("flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em]", live ? "text-signal" : detail.status === "completed" ? "text-success" : "text-muted-foreground")}>
              <span className={cn("h-1.5 w-1.5", live ? "animate-pulse bg-signal" : detail.status === "completed" ? "bg-success" : "bg-muted-foreground")} />
              {titleCase(detail.status)}
            </span>
            <span className="font-mono text-[12px] text-muted-foreground tabular">
              {recorded} / {planned} executions
            </span>
            {detail.is_simulated ? <span className="border border-signal/40 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-signal">Simulated</span> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {detail.programme_id ? (
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/programmes/${detail.programme_id}`}>Programme</Link>
              </Button>
            ) : null}
            {live ? (
              <Button variant="outline" size="sm" onClick={cancel}>
                Cancel run
              </Button>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={rerun}>
                  Rerun programme
                </Button>
                {detail.status === "completed" ? <GenerateReportButton assessmentId={detail.id} /> : null}
              </>
            )}
          </div>
        </div>
        <div className="flex h-1 gap-px bg-border">
          {OUTCOMES.map((key) => (counts[key] ? <span key={key} className={outcomeFill[key]} style={{ width: `${(counts[key] / planned) * 100}%` }} /> : null))}
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-1 px-5 py-2.5 font-mono text-[11px]">
          {OUTCOMES.map((key) => (
            <span key={key} className={outcomeTone[key]}>
              {key.toLowerCase()} {counts[key] ?? 0}
            </span>
          ))}
        </div>
        {detail.error_summary ? <p className="border-t border-border px-5 py-3 text-[13px] text-destructive">{detail.error_summary}</p> : null}
      </section>

      {report ? (
        <>
          <section className="grid gap-8 border-b border-border pb-8 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1.4fr_1.2fr]">
            <ScoreFigure label={`${report.industry_name} score`} block={report.industry_score} note="Industry scenarios only." />
            <ScoreFigure label="Overall score" block={report.overall_score} note={report.generic_score ? "Industry scenarios plus generic checks." : "No generic checks in this run."} />
            <div>
              <Kicker>Outcomes</Kicker>
              <OutcomeBar counts={report.outcomes} className="mt-4 h-2" />
              <dl className="mt-3 space-y-1.5">
                {(["FAIL", "INCONCLUSIVE", "ERROR"] as const).map((key) => (
                  <div key={key} className="grid grid-cols-[6.5rem_2rem_minmax(0,1fr)] gap-2 text-[11px] leading-4">
                    <dt className={cn("font-mono", outcomeTone[key])}>{key.toLowerCase()}</dt>
                    <dd className="font-mono tabular text-foreground">{report.outcomes[key] ?? 0}</dd>
                    <dd className="text-faint">{report.definitions[key]}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div>
              <Kicker>Coverage</Kicker>
              <p className="mt-2 font-display text-4xl leading-none tabular">
                {report.coverage.executed}
                <span className="text-2xl text-faint">/{report.coverage.planned}</span>
              </p>
              <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
                Executions produced a pass or fail. {report.coverage.inconclusive} inconclusive, {report.coverage.could_not_execute} could not execute.
              </p>
              <p className="mt-1 text-[12px] leading-5 text-faint">
                Threat classes tested: {report.coverage.threats_tested.length} of {report.coverage.threats_in_library.length} in the {report.industry_name.toLowerCase()} library.
              </p>
            </div>
          </section>

          {report.comparison ? (
            <section className="flex flex-wrap items-center gap-x-8 gap-y-3 border border-border px-5 py-4">
              <div>
                <Kicker>Against previous run</Kicker>
                <Link href={`/assessments/${report.comparison.previous_id}`} className="mt-1 block text-[13px] text-muted-foreground underline decoration-input underline-offset-4 hover:text-foreground">
                  {report.comparison.previous_name}
                </Link>
              </div>
              <p className={cn("font-display text-3xl tabular", (report.comparison.score_delta ?? 0) > 0 ? "text-success" : (report.comparison.score_delta ?? 0) < 0 ? "text-destructive" : "text-muted-foreground")}>
                {report.comparison.score_delta === null ? "—" : `${report.comparison.score_delta > 0 ? "+" : ""}${report.comparison.score_delta}`}
              </p>
              {[
                ["resolved_vulnerability", "resolved", "text-success"],
                ["new_vulnerability", "new", "text-destructive"],
                ["persistent_vulnerability", "persistent", "text-signal"],
              ].map(([key, label, tone]) => (
                <p key={key} className="font-mono text-[12px] text-muted-foreground">
                  <span className={cn("mr-1.5 text-lg tabular", tone)}>{report.comparison?.counts[key] ?? 0}</span>
                  {label}
                </p>
              ))}
            </section>
          ) : null}

          <section className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <div>
              <Kicker>By threat class</Kicker>
              <ul className="mt-3 border-t border-border">
                {report.by_threat.map((row) => (
                  <li key={row.key} className="grid grid-cols-[3.5rem_minmax(0,1fr)_7rem] items-center gap-3 border-b border-border py-3">
                    <span className="font-mono text-[11px] text-faint">{row.key}</span>
                    <div className="min-w-0">
                      <p className="truncate text-[13px]">{row.label}</p>
                      <OutcomeBar counts={{ PASS: row.PASS, FAIL: row.FAIL, INCONCLUSIVE: row.INCONCLUSIVE, ERROR: row.ERROR, SKIPPED: row.SKIPPED }} className="mt-1.5" />
                    </div>
                    <span className="text-right font-mono text-[11px] tabular text-muted-foreground">
                      <span className="text-destructive">{row.FAIL}</span> / {row.PASS + row.FAIL + row.INCONCLUSIVE + row.ERROR + row.SKIPPED}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <Kicker>Critical vulnerabilities · {report.critical.length}</Kicker>
              {report.critical.length === 0 ? (
                <p className="mt-3 border-t border-border pt-3 text-[13px] text-muted-foreground">No critical-severity failure was observed in this run.</p>
              ) : (
                <ul className="mt-3 border-t border-border">
                  {report.critical.map((item) => (
                    <li key={item.code} className="border-b border-border py-3">
                      <p className="text-[13px] text-foreground">{item.title}</p>
                      <p className="mt-1 text-[12px] leading-5 text-muted-foreground">{item.summary}</p>
                      <p className="mt-1 font-mono text-[10px] text-faint">
                        {item.code} · {item.threat}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      ) : live ? null : (
        <p className="text-[13px] text-muted-foreground">Preparing the intelligence report…</p>
      )}

      <section>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <Kicker>Scenario results</Kicker>
          <div className="flex max-w-full overflow-x-auto border border-border" role="group" aria-label="Filter by outcome">
            {["all", ...OUTCOMES].map((key) => (
              <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)} className={cn("h-7 px-2.5 font-mono text-[10px] uppercase tracking-[0.08em]", filter === key ? "bg-secondary text-foreground" : "text-faint hover:text-muted-foreground")}>
                {key === "all" ? `all ${recorded}` : `${key.toLowerCase()} ${counts[key] ?? 0}`}
              </button>
            ))}
          </div>
        </div>
        <ul className="mt-3 border border-border">
          {results.length === 0 ? <li className="px-4 py-8 text-center text-[13px] text-faint">{live ? "Results appear as each scenario finishes." : "No results with this outcome."}</li> : null}
          {results.map((result) => {
            const row = rowsById[result.id];
            const expanded = open === result.id;
            return (
              <li key={result.id} className="border-b border-border/70 last:border-b-0">
                <button type="button" onClick={() => setOpen(expanded ? null : result.id)} aria-expanded={expanded} className={cn("grid w-full grid-cols-[6.5rem_minmax(0,1fr)] gap-3 px-4 py-3 text-left transition-colors md:grid-cols-[6.5rem_minmax(0,1fr)_4rem_6.5rem]", expanded ? "bg-secondary" : "hover:bg-secondary/50")}>
                  <OutcomeLabel outcome={result.outcome} />
                  <span className="min-w-0">
                    <span className="block truncate text-[13px]">{result.evidence.scenario?.name ?? result.title}</span>
                    <span className="mt-0.5 block truncate text-[12px] text-faint">{result.summary}</span>
                  </span>
                  <span className="hidden font-mono text-[11px] text-muted-foreground md:block">{row?.threat ?? (result.evidence.engine ? "" : "generic")}</span>
                  <span className="hidden md:block">{row?.severity ? <RiskMark risk={row.severity} /> : <span className="font-mono text-[11px] text-faint">{row?.risk ?? ""}</span>}</span>
                </button>
                {expanded ? (
                  <div className="border-t border-border px-4 py-5 md:px-6">
                    <ResultEvidence result={result} />
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      {report?.remediation.length ? (
        <section>
          <Kicker>Remediation plan</Kicker>
          <ol className="mt-3 border-t border-border">
            {report.remediation.map((item, index) => (
              <li key={item.step} className="grid grid-cols-[2rem_minmax(0,1fr)_7rem] gap-3 border-b border-border py-3 text-[13px] leading-6">
                <span className="font-mono text-[11px] text-faint">{String(index + 1).padStart(2, "0")}</span>
                <span>
                  {item.step}
                  <span className="mt-0.5 block font-mono text-[10px] text-faint">from {item.source}</span>
                </span>
                <span className="text-right">{item.severity ? <RiskMark risk={item.severity} /> : null}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section className="border border-border">
        <button type="button" onClick={() => setShowLog((value) => !value)} aria-expanded={showLog} className="flex w-full items-center justify-between px-4 py-2.5 text-left">
          <Kicker>Execution log · {logs.length} events</Kicker>
          <span className="text-[12px] text-faint">{showLog ? "Hide" : "Show"}</span>
        </button>
        {showLog ? (
          <div className="border-t border-border bg-background/40">
            <ExecutionLog entries={logs} live={live} />
          </div>
        ) : null}
      </section>

      {report ? <p className="text-[11px] leading-5 text-faint">{report.disclaimer}</p> : null}
    </div>
  );
}
