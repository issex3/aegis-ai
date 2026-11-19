"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Field } from "@/components/field";
import { Kicker } from "@/components/intel/marks";
import { TagInput } from "@/components/intel/tag-input";
import { Button } from "@/components/ui/button";
import { clientApi, fieldErrors } from "@/lib/api";
import type { AgentProfile, LibraryIndex, ProfileAnalysis, Programme } from "@/lib/types";
import { cn } from "@/lib/utils";

const BASELINE = new Set(["conversation.untrusted", "instructions.confidential"]);
const SENSITIVITY = [
  { value: "low", label: "Low", note: "Internal helper, no customer data or actions." },
  { value: "moderate", label: "Moderate", note: "Reads business data, limited actions." },
  { value: "high", label: "High", note: "Handles personal or financial data, or acts on systems." },
  { value: "critical", label: "Critical", note: "Moves money, handles health or privileged data." },
] as const;

type Draft = Omit<AgentProfile, "id" | "agent_id" | "capabilities" | "analysis" | "version" | "updated_at">;

function emptyDraft(industry: string): Draft {
  return {
    industry,
    description: "",
    purpose: "",
    responsibilities: [],
    tools: [],
    permissions: [],
    data_types: [],
    authorised_actions: [],
    risk_sensitivity: "moderate",
  };
}


export function ProfileEditor({ agentId, agentName, profile, index }: { agentId: string; agentName: string; profile: AgentProfile | null; index: LibraryIndex }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(() =>
    profile
      ? {
          industry: profile.industry,
          description: profile.description,
          purpose: profile.purpose,
          responsibilities: profile.responsibilities,
          tools: profile.tools,
          permissions: profile.permissions,
          data_types: profile.data_types,
          authorised_actions: profile.authorised_actions,
          risk_sensitivity: profile.risk_sensitivity,
        }
      : emptyDraft(index.industries[0]?.slug ?? ""),
  );
  const [analysis, setAnalysis] = useState<ProfileAnalysis | null>(profile?.analysis ?? null);
  const [confirmed, setConfirmed] = useState<string[] | null>(profile ? profile.capabilities : null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<"save" | "build" | null>(null);
  const [adding, setAdding] = useState("");

  const capabilityMeta = useMemo(() => Object.fromEntries(index.capabilities.map((item) => [item.key, item])), [index.capabilities]);
  const industry = index.industries.find((item) => item.slug === draft.industry);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const result = await clientApi<ProfileAnalysis>("/profile-analysis", { method: "POST", body: JSON.stringify(draft) });
      if (result.ok) setAnalysis(result.data);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [draft]);

  const inferred = analysis?.capabilities.map((item) => item.key) ?? [];
  const active = new Set(confirmed ?? inferred);
  BASELINE.forEach((key) => active.add(key));
  const evidence = Object.fromEntries((analysis?.capabilities ?? []).map((item) => [item.key, item]));
  const shown = Array.from(new Set([...inferred, ...(confirmed ?? [])])).filter((key) => capabilityMeta[key]);
  const remaining = index.capabilities.filter((item) => !shown.includes(item.key));

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function toggle(key: string) {
    if (BASELINE.has(key)) return;
    const next = new Set(active);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setConfirmed(Array.from(next));
  }

  async function save(): Promise<boolean> {
    setErrors({});
    const result = await clientApi<{ profile: AgentProfile }>(`/agents/${agentId}/profile`, {
      method: "PUT",
      body: JSON.stringify({ ...draft, capabilities: Array.from(active) }),
    });
    if (!result.ok) {
      setErrors(fieldErrors(result.error));
      toast.error(result.error.error.message);
      return false;
    }
    setConfirmed(result.data.profile.capabilities);
    return true;
  }

  async function onSave() {
    setPending("save");
    const ok = await save();
    setPending(null);
    if (ok) {
      toast.success("Profile saved.");
      router.refresh();
    }
  }

  async function onBuild() {
    setPending("build");
    const ok = await save();
    if (!ok) {
      setPending(null);
      return;
    }
    const created = await clientApi<Programme>("/programmes", { method: "POST", body: JSON.stringify({ agent_id: agentId, intensity: "standard" }) });
    setPending(null);
    if (!created.ok) {
      toast.error(created.error.error.message);
      return;
    }
    router.push(`/programmes/${created.data.id}`);
  }

  return (
    <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-10">
        <section>
          <Kicker>01 · Industry</Kicker>
          <div className="mt-3 grid border-l border-t border-border sm:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label="Industry">
            {index.industries.map((item) => (
              <button
                key={item.slug}
                type="button"
                role="radio"
                aria-checked={draft.industry === item.slug}
                onClick={() => update("industry", item.slug)}
                className={cn("relative border-b border-r border-border p-4 text-left transition-colors", draft.industry === item.slug ? "bg-secondary" : "bg-card hover:bg-secondary/50")}
              >
                {draft.industry === item.slug ? <span className="absolute inset-x-0 top-0 h-px bg-signal" aria-hidden="true" /> : null}
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-[14px] font-medium">{item.name}</span>
                  <span className="font-mono text-[10px] text-faint">{item.scenarios} scenarios</span>
                </span>
                <span className="mt-1.5 block text-[12px] leading-5 text-muted-foreground">{item.summary}</span>
              </button>
            ))}
          </div>
          {errors.industry ? <p className="mt-1 text-[12px] text-destructive">{errors.industry}</p> : null}
        </section>

        <section className="space-y-6">
          <Kicker>02 · What the agent does</Kicker>
          <Field label="Describe the agent in your own words" htmlFor="description" hint="Plain language is fine. Mention what it reads, what it can change, who talks to it, and which systems it connects to." error={errors.description}>
            <textarea
              id="description"
              rows={5}
              value={draft.description}
              onChange={(event) => update("description", event.target.value)}
              placeholder="For example: answers customer emails, looks up orders, can issue refunds under £100, and escalates complaints to a human."
              className="w-full border border-input bg-background px-3 py-2 text-[14px] leading-6 outline-none placeholder:text-faint focus:border-muted-foreground"
            />
          </Field>
          <Field label="Primary purpose" htmlFor="purpose" error={errors.purpose}>
            <input
              id="purpose"
              value={draft.purpose}
              onChange={(event) => update("purpose", event.target.value)}
              placeholder="One sentence."
              className="h-9 w-full border border-input bg-background px-3 text-[14px] outline-none placeholder:text-faint focus:border-muted-foreground"
            />
          </Field>
          <div className="grid gap-6 md:grid-cols-2">
            <Field label="Primary responsibilities" htmlFor="responsibilities" hint="Press Enter after each item.">
              <TagInput id="responsibilities" values={draft.responsibilities} onChange={(value) => update("responsibilities", value)} placeholder="Handle refund requests" />
            </Field>
            <Field label="Connected tools and integrations" htmlFor="tools" hint="Systems, APIs, inboxes.">
              <TagInput id="tools" values={draft.tools} onChange={(value) => update("tools", value)} placeholder="Zendesk, Stripe" />
            </Field>
            <Field label="Available permissions" htmlFor="permissions">
              <TagInput id="permissions" values={draft.permissions} onChange={(value) => update("permissions", value)} placeholder="Read orders" />
            </Field>
            <Field label="Actions it is authorised to perform" htmlFor="actions">
              <TagInput id="actions" values={draft.authorised_actions} onChange={(value) => update("authorised_actions", value)} placeholder="Issue refund up to £100" />
            </Field>
          </div>
        </section>

        <section className="space-y-6">
          <Kicker>03 · Information and sensitivity</Kicker>
          <Field label="Types of information it accesses" htmlFor="data-types">
            <div id="data-types" className="flex flex-wrap gap-2">
              {index.data_classes.map((item) => {
                const on = draft.data_types.includes(item.key);
                return (
                  <button
                    key={item.key}
                    type="button"
                    aria-pressed={on}
                    onClick={() => update("data_types", on ? draft.data_types.filter((value) => value !== item.key) : [...draft.data_types, item.key])}
                    className={cn("border px-2.5 py-1 text-[12px] transition-colors", on ? "border-signal/60 bg-signal/10 text-foreground" : "border-border text-muted-foreground hover:border-input")}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </Field>
          <Field label="Risk sensitivity" htmlFor="sensitivity" hint="Raises or lowers the priority of applicable scenarios.">
            <div id="sensitivity" className="grid border border-border sm:grid-cols-4" role="radiogroup" aria-label="Risk sensitivity">
              {SENSITIVITY.map((item, position) => (
                <button
                  key={item.value}
                  type="button"
                  role="radio"
                  aria-checked={draft.risk_sensitivity === item.value}
                  onClick={() => update("risk_sensitivity", item.value)}
                  className={cn(
                    "p-3 text-left transition-colors",
                    position > 0 && "border-t border-border sm:border-l sm:border-t-0",
                    draft.risk_sensitivity === item.value ? "bg-secondary" : "hover:bg-secondary/50",
                  )}
                >
                  <span className={cn("text-[13px] font-medium", draft.risk_sensitivity === item.value && "text-signal")}>{item.label}</span>
                  <span className="mt-1 block text-[11px] leading-4 text-faint">{item.note}</span>
                </button>
              ))}
            </div>
          </Field>
        </section>

        <div className="flex flex-wrap items-center gap-3 border-t border-border pt-6">
          <Button onClick={onBuild} disabled={pending !== null}>
            {pending === "build" ? "Building programme…" : "Save and build testing programme"}
          </Button>
          <Button variant="outline" onClick={onSave} disabled={pending !== null}>
            {pending === "save" ? "Saving…" : "Save profile"}
          </Button>
          {profile ? <span className="font-mono text-[11px] text-faint">profile v{profile.version}</span> : null}
        </div>
      </div>

      <aside className="xl:sticky xl:top-20 xl:self-start">
        <div className="border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <Kicker>Capability analysis · {agentName}</Kicker>
            <p className="mt-1.5 text-[12px] leading-5 text-muted-foreground">
              Inferred from the fields on the left by keyword analysis, not by a model. Each capability shows what triggered it. Scenarios apply only where a confirmed capability exposes the agent.
            </p>
          </div>
          <ul className="max-h-[26rem] overflow-auto">
            {shown.length === 0 ? <li className="px-4 py-6 text-[12px] text-faint">Describe the agent to see capabilities.</li> : null}
            {shown.map((key) => {
              const meta = capabilityMeta[key];
              const on = active.has(key);
              const locked = BASELINE.has(key);
              const source = evidence[key]?.evidence?.[0];
              return (
                <li key={key} className="border-b border-border/70 last:border-b-0">
                  <button type="button" onClick={() => toggle(key)} disabled={locked} aria-pressed={on} className="flex w-full items-start gap-3 px-4 py-2.5 text-left disabled:cursor-default">
                    <span className={cn("mt-1 grid h-3.5 w-3.5 shrink-0 place-items-center border", on ? "border-signal bg-signal" : "border-input")} aria-hidden="true">
                      {on ? <span className="h-1.5 w-1.5 bg-background" /> : null}
                    </span>
                    <span className="min-w-0">
                      <span className={cn("block text-[13px]", on ? "text-foreground" : "text-muted-foreground line-through decoration-faint")}>{meta.label}</span>
                      <span className="mt-0.5 block truncate font-mono text-[10px] text-faint">
                        {locked ? "baseline · always tested" : source ? `${source.field} · "${source.term}"` : "added manually"}
                        {meta.kind === "action" ? " · action" : ""}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {analysis?.missing_typical.length ? (
            <div className="border-t border-border px-4 py-3">
              <p className="text-[12px] text-faint">Typical for {industry?.name ?? "this industry"} but not described:</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {analysis.missing_typical
                  .filter((item) => !active.has(item.key))
                  .map((item) => (
                    <button key={item.key} type="button" onClick={() => toggle(item.key)} className="border border-dashed border-input px-2 py-0.5 text-[11px] text-muted-foreground hover:border-muted-foreground hover:text-foreground">
                      + {item.label}
                    </button>
                  ))}
              </div>
            </div>
          ) : null}
          <div className="flex gap-2 border-t border-border px-4 py-3">
            <select aria-label="Add a capability" value={adding} onChange={(event) => setAdding(event.target.value)} className="h-8 min-w-0 flex-1 border border-border bg-background px-2 text-[12px]">
              <option value="">Add another capability…</option>
              {remaining.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="outline"
              disabled={!adding}
              onClick={() => {
                toggle(adding);
                setAdding("");
              }}
            >
              Add
            </Button>
          </div>
          {analysis?.data_classes.length ? (
            <div className="border-t border-border px-4 py-3">
              <p className="text-[12px] text-faint">Data classes in scope</p>
              <p className="mt-1 text-[12px] leading-5 text-muted-foreground">{analysis.data_classes.map((item) => `${item.label} (${item.source})`).join(" · ")}</p>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
