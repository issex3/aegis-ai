"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Kicker, PriorityLabel, RiskMark, Stat } from "@/components/intel/marks";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import { assessmentCategories, formatWhen, titleCase } from "@/lib/labels";
import type { Programme, SelectionEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

const INTENSITY_LABELS = { focused: "Focused", standard: "Standard", extended: "Extended" } as const;

function Checkbox({ checked, onChange, label }: { checked: boolean; onChange: () => void; label: string }) {
  return (
    <button type="button" role="checkbox" aria-checked={checked} aria-label={label} onClick={onChange} className={cn("grid h-4 w-4 shrink-0 place-items-center border transition-colors", checked ? "border-signal bg-signal" : "border-input hover:border-muted-foreground")}>
      {checked ? <span className="h-1.5 w-1.5 bg-background" /> : null}
    </button>
  );
}

function ScenarioRow({ entry, onToggle, expanded, onExpand }: { entry: SelectionEntry; onToggle: () => void; expanded: boolean; onExpand: () => void }) {
  return (
    <li className={cn("border-b border-border/70 last:border-b-0", !entry.selected && "opacity-70")}>
      <div className="grid grid-cols-[1rem_2rem_minmax(0,1fr)] items-start gap-3 px-4 py-3 md:grid-cols-[1rem_2rem_minmax(0,1fr)_4rem_6.5rem_2rem] md:items-center">
        <Checkbox checked={entry.selected} onChange={onToggle} label={`Include ${entry.name}`} />
        <PriorityLabel priority={entry.priority} />
        <div className="min-w-0">
          <Link href={`/library/${entry.code}`} className="block truncate text-[14px] hover:underline hover:underline-offset-4">
            {entry.name}
          </Link>
          <p className="mt-0.5 truncate font-mono text-[11px] text-faint">
            {entry.code}
            {entry.variants ? ` · +${entry.variants} variant` : ""}
            {entry.override ? " · included manually" : ""}
          </p>
        </div>
        <span className="hidden font-mono text-[11px] text-muted-foreground md:block" title={entry.threat_name}>
          {entry.threat}
        </span>
        <RiskMark risk={entry.risk} className="hidden md:inline-flex" />
        <button type="button" onClick={onExpand} aria-expanded={expanded} className="grid h-8 w-8 place-items-center text-faint hover:text-foreground md:h-6 md:w-6" aria-label="Why this scenario">
          <span className={cn("transition-transform", expanded && "rotate-90")}>›</span>
        </button>
      </div>
      {expanded ? (
        <div className="border-t border-border/70 bg-background/40 px-4 py-3 pl-4 text-[12px] leading-5 text-muted-foreground md:pl-[4.75rem]">
          {entry.applicable ? (
            <ul className="space-y-1">
              {entry.rationale.map((line) => (
                <li key={line}>{line}</li>
              ))}
              <li className="font-mono text-[10px] text-faint">priority score {entry.priority_points}</li>
            </ul>
          ) : (
            <p>{entry.reason}</p>
          )}
        </div>
      ) : null}
    </li>
  );
}

export function ProgrammeBuilder({ initial }: { initial: Programme }) {
  const router = useRouter();
  const [programme, setProgramme] = useState(initial);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState(`${initial.industry_name} programme · ${initial.agent_name}`);
  const [note, setNote] = useState("");
  const [authorised, setAuthorised] = useState(false);
  const [launching, setLaunching] = useState(false);

  async function patch(body: Record<string, unknown>) {
    setSaving(true);
    const result = await clientApi<Programme>(`/programmes/${programme.id}`, { method: "PATCH", body: JSON.stringify(body) });
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    setProgramme(result.data);
  }

  function setSelected(codes: string[]) {
    setProgramme((current) => ({ ...current, selection: current.selection.map((entry) => ({ ...entry, selected: codes.includes(entry.code) })) }));
    void patch({ selected: codes });
  }

  const selectedCodes = programme.selection.filter((entry) => entry.selected).map((entry) => entry.code);
  const applicable = programme.selection.filter((entry) => entry.applicable);
  const excluded = programme.selection.filter((entry) => !entry.applicable);

  function toggle(code: string) {
    setSelected(selectedCodes.includes(code) ? selectedCodes.filter((item) => item !== code) : [...selectedCodes, code]);
  }

  async function launch() {
    setLaunching(true);
    const result = await clientApi<{ assessment_id: string }>(`/programmes/${programme.id}/launch`, {
      method: "POST",
      body: JSON.stringify({ name, authorised, authorisation_note: note }),
    });
    setLaunching(false);
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    router.push(`/assessments/${result.data.assessment_id}`);
  }

  const threats = Object.entries(programme.stats.threats);
  const maxThreat = Math.max(1, ...threats.map(([, value]) => value.applicable));

  return (
    <div className="space-y-8">
      <section className="grid gap-6 border border-border bg-card p-5 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Applicable" value={programme.stats.applicable} note={`of ${programme.stats.library} ${programme.industry_name.toLowerCase()} scenarios`} />
        <Stat label="Selected" value={programme.stats.selected} note={`${programme.stats.by_priority.P1 ?? 0} priority 1 · ${programme.stats.overrides} manual`} />
        <Stat label="Executions" value={programme.stats.executions + programme.stats.generic} note={`${programme.stats.executions} scenario runs, ${programme.stats.generic} generic checks`} />
        <Stat label="Not applicable" value={programme.stats.not_applicable} note="Excluded by the profile, with reasons" tone="text-muted-foreground" />
      </section>

      <section className="flex flex-wrap items-start gap-x-8 gap-y-3 border-b border-border pb-6 text-[12px]">
        <div>
          <Kicker>Profile v{programme.profile.version}</Kicker>
          <p className="mt-1.5 max-w-md leading-5 text-muted-foreground">{programme.profile.purpose}</p>
        </div>
        <div className="min-w-0 basis-full md:basis-0 md:flex-1">
          <Kicker>Confirmed capabilities</Kicker>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {programme.profile.capabilities.map((item) => (
              <span key={item.key} className="border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">
                {item.label}
              </span>
            ))}
          </div>
        </div>
        <div>
          <Kicker>Sensitivity</Kicker>
          <p className="mt-1.5 text-muted-foreground">{titleCase(programme.profile.risk_sensitivity)}</p>
        </div>
        <Link href={`/agents/${programme.agent_id}/profile`} className="self-center text-[12px] text-muted-foreground underline decoration-input underline-offset-4 hover:text-foreground">
          Edit profile
        </Link>
      </section>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <Kicker>Testing intensity</Kicker>
              <div className="mt-2 inline-flex border border-border" role="radiogroup" aria-label="Testing intensity">
                {(Object.keys(INTENSITY_LABELS) as (keyof typeof INTENSITY_LABELS)[]).map((key) => (
                  <button
                    key={key}
                    type="button"
                    role="radio"
                    aria-checked={programme.intensity === key}
                    onClick={() => void patch({ intensity: key })}
                    className={cn("h-8 px-3 text-[13px] transition-colors", programme.intensity === key ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground")}
                  >
                    {INTENSITY_LABELS[key]}
                  </button>
                ))}
              </div>
              <p className="mt-2 max-w-md text-[12px] leading-5 text-faint">{programme.intensities[programme.intensity]}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[12px]">
              {saving ? <span className="font-mono text-[11px] text-faint">saving…</span> : null}
              <button type="button" onClick={() => setSelected(applicable.map((entry) => entry.code))} className="text-muted-foreground hover:text-foreground">
                Select all applicable
              </button>
              <span className="text-border">|</span>
              <button type="button" onClick={() => setSelected([])} className="text-muted-foreground hover:text-foreground">
                Clear
              </button>
              <span className="text-border">|</span>
              <button type="button" onClick={() => void patch({ intensity: programme.intensity })} className="text-muted-foreground hover:text-foreground">
                Reset to recommended
              </button>
            </div>
          </div>

          <div className="mt-5 border border-border">
            <div className="flex items-baseline justify-between border-b border-border px-4 py-2.5">
              <Kicker>Recommended for this agent · {applicable.length}</Kicker>
              <span className="hidden font-mono text-[10px] uppercase tracking-[0.14em] text-faint md:block">priority · threat · risk</span>
            </div>
            <ul>
              {applicable.map((entry) => (
                <ScenarioRow key={entry.code} entry={entry} onToggle={() => toggle(entry.code)} expanded={expanded === entry.code} onExpand={() => setExpanded(expanded === entry.code ? null : entry.code)} />
              ))}
            </ul>
          </div>

          {excluded.length ? (
            <div className="mt-4 border border-border">
              <button type="button" onClick={() => setShowExcluded((value) => !value)} aria-expanded={showExcluded} className="flex w-full items-center justify-between px-4 py-2.5 text-left">
                <Kicker>Not applicable to this profile · {excluded.length}</Kicker>
                <span className="text-[12px] text-faint">{showExcluded ? "Hide" : "Show reasons"}</span>
              </button>
              {showExcluded ? (
                <ul className="border-t border-border">
                  {excluded.map((entry) => (
                    <li key={entry.code} className="grid grid-cols-[1rem_minmax(0,1fr)] gap-3 border-b border-border/70 px-4 py-3 last:border-b-0">
                      <Checkbox checked={entry.selected} onChange={() => toggle(entry.code)} label={`Include ${entry.name} anyway`} />
                      <div className="min-w-0">
                        <p className="text-[13px] text-muted-foreground">
                          {entry.name} <span className="font-mono text-[11px] text-faint">· {entry.threat} · {entry.risk}</span>
                        </p>
                        <p className="mt-0.5 text-[12px] leading-5 text-faint">{entry.reason}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>

        <aside className="space-y-6 xl:sticky xl:top-20 xl:self-start">
          <section className="border border-border bg-card p-4">
            <Kicker>Threat coverage</Kicker>
            <ul className="mt-3 space-y-2.5">
              {threats.map(([key, value]) => (
                <li key={key}>
                  <div className="flex items-baseline justify-between gap-2 text-[12px]">
                    <span className="truncate text-muted-foreground">
                      <span className="font-mono text-[11px] text-faint">{key}</span> {value.name}
                    </span>
                    <span className="font-mono text-[11px] tabular text-muted-foreground">
                      {value.selected}/{value.applicable}
                    </span>
                  </div>
                  <div className="mt-1 h-1 bg-border">
                    <div className="relative h-full bg-input" style={{ width: `${(value.applicable / maxThreat) * 100}%` }}>
                      <div className="absolute inset-y-0 left-0 bg-signal" style={{ width: value.applicable ? `${(Math.min(value.selected, value.applicable) / value.applicable) * 100}%` : "0%" }} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <Kicker>Generic security checks</Kicker>
              <Checkbox checked={programme.include_generic} onChange={() => void patch({ include_generic: !programme.include_generic })} label="Include generic checks" />
            </div>
            <p className="mt-2 text-[12px] leading-5 text-muted-foreground">Single-turn checks that apply to any agent. Leave every category off to include all ten.</p>
            {programme.include_generic ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {assessmentCategories.map(([value, label]) => {
                  const on = programme.generic_categories.includes(value);
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={on}
                      onClick={() => void patch({ generic_categories: on ? programme.generic_categories.filter((item) => item !== value) : [...programme.generic_categories, value] })}
                      className={cn("border px-2 py-0.5 text-[11px]", on ? "border-signal/60 text-foreground" : "border-border text-faint hover:text-muted-foreground")}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </section>

          <section className="border border-border bg-card p-4">
            <Kicker>Launch</Kicker>
            <label htmlFor="run-name" className="mt-3 block text-[12px] text-muted-foreground">
              Run name
            </label>
            <input id="run-name" value={name} onChange={(event) => setName(event.target.value)} className="mt-1 h-8 w-full border border-input bg-background px-2 text-[13px] outline-none focus:border-muted-foreground" />
            <label htmlFor="auth-note" className="mt-3 block text-[12px] text-muted-foreground">
              Authorisation note
            </label>
            <textarea id="auth-note" rows={2} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Who authorised this test and why." className="mt-1 w-full border border-input bg-background px-2 py-1.5 text-[13px] outline-none placeholder:text-faint focus:border-muted-foreground" />
            <label className="mt-3 flex items-start gap-2 text-[12px] leading-5 text-muted-foreground">
              <input type="checkbox" checked={authorised} onChange={(event) => setAuthorised(event.target.checked)} className="mt-0.5" />I am authorised to send these scenarios to this agent.
            </label>
            <Button className="mt-4 w-full" onClick={launch} disabled={launching || !authorised || note.trim().length < 10 || programme.stats.executions + programme.stats.generic === 0}>
              {launching ? "Starting…" : `Run ${programme.stats.executions + programme.stats.generic} executions`}
            </Button>
            <p className="mt-3 text-[11px] leading-4 text-faint">
              Runs in the background against synthetic sandboxes only.{programme.agent_simulated ? " This agent is the local demo, so results are simulated." : ""}
            </p>
          </section>

          {programme.runs.length ? (
            <section>
              <Kicker>Runs from this programme</Kicker>
              <ul className="mt-2 border-t border-border">
                {programme.runs.map((run) => (
                  <li key={run.id} className="border-b border-border">
                    <Link href={`/assessments/${run.id}`} className="flex items-baseline justify-between gap-3 py-2 text-[12px] hover:text-foreground">
                      <span className="truncate text-muted-foreground">{run.name}</span>
                      <span className="shrink-0 font-mono text-[10px] text-faint">{formatWhen(run.created_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
