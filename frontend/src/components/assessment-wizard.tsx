"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Field } from "@/components/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clientApi } from "@/lib/api";
import { assessmentCategories } from "@/lib/labels";
import type { Agent, Assessment, Sandbox } from "@/lib/types";

type Preview = { code: string; title: string; category: string; severity: string; requires_tools: boolean };

export function AssessmentWizard({ agents, sandboxes }: { agents: Agent[]; sandboxes: Sandbox[] }) {
  const router = useRouter();
  const runnable = agents.filter((agent) => agent.status === "active" && agent.adapter_status !== "not_implemented");
  const [agentId, setAgentId] = useState(runnable[0]?.id ?? "");
  const [sandboxId, setSandboxId] = useState("");
  const [categories, setCategories] = useState<string[]>(assessmentCategories.map(([value]) => value));
  const [name, setName] = useState("Security assessment");
  const [note, setNote] = useState("");
  const [authorised, setAuthorised] = useState(false);
  const [preview, setPreview] = useState<Preview[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const query = sandboxId ? `?sandbox_id=${sandboxId}` : "";
    clientApi<{ cases: Preview[] }>(`/assessment-catalogue${query}`).then((result) => {
      if (result.ok) {
        setPreview(result.data.cases.filter((item) => categories.includes(item.category)));
      }
    });
  }, [sandboxId, categories]);

  function toggle(category: string) {
    setCategories((current) => (current.includes(category) ? current.filter((item) => item !== category) : [...current, category]));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    const planned = await clientApi<Assessment>("/assessments/plan", {
      method: "POST",
      body: JSON.stringify({
        agent_id: agentId,
        name,
        sandbox_id: sandboxId || null,
        categories,
        authorised,
        authorisation_note: note,
      }),
    });
    if (!planned.ok) {
      setPending(false);
      setMessage(planned.error.error.message);
      return;
    }
    const started = await clientApi(`/assessments/${planned.data.id}/run`, { method: "POST" });
    setPending(false);
    if (!started.ok) {
      setMessage(started.error.error.message);
      return;
    }
    router.push(`/assessments/${planned.data.id}`);
    router.refresh();
  }

  if (runnable.length === 0) {
    return <p className="text-sm text-muted-foreground">Add the demo agent or an OpenAI-compatible agent before running an assessment. Other adapters are not implemented.</p>;
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <p className="text-sm text-muted-foreground">Sandbox tools use fictional records. A result does not prove that the agent’s real external systems are safe.</p>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Agent" htmlFor="agent">
          <select id="agent" className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={agentId} onChange={(event) => setAgentId(event.target.value)}>
            {runnable.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} {agent.adapter_status === "demo" ? "(simulated)" : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Sandbox" htmlFor="sandbox" hint="Generic checks always run. A sandbox adds its tools and records.">
          <select id="sandbox" className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={sandboxId} onChange={(event) => setSandboxId(event.target.value)}>
            <option value="">Generic suite only</option>
            {sandboxes.map((sandbox) => (
              <option key={sandbox.id} value={sandbox.id}>
                {sandbox.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Assessment name" htmlFor="assessment-name">
        <Input id="assessment-name" value={name} onChange={(event) => setName(event.target.value)} required />
      </Field>
      <fieldset>
        <legend className="text-sm font-medium">Categories</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {assessmentCategories.map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 text-sm text-muted-foreground">
              <input type="checkbox" checked={categories.includes(value)} onChange={() => toggle(value)} />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      <div>
        <h3 className="text-sm font-medium">Scope</h3>
        <p className="mt-1 text-sm text-muted-foreground">{preview.length} test cases will run. Tool cases that the integration cannot expose are recorded as inconclusive, not as passes.</p>
        <ul className="mt-3 max-h-48 space-y-1 overflow-auto text-sm">
          {preview.map((item) => (
            <li key={item.code} className="flex justify-between gap-3 border-b border-border py-1">
              <span>{item.title}</span>
              <span className="font-mono text-xs text-muted-foreground">{item.severity}</span>
            </li>
          ))}
        </ul>
      </div>
      <Field label="Authorisation" htmlFor="note" hint="State that you are allowed to send these tests to the selected agent.">
        <Input id="note" value={note} onChange={(event) => setNote(event.target.value)} required minLength={10} />
      </Field>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={authorised} onChange={(event) => setAuthorised(event.target.checked)} />
        I am authorised to run this assessment against this agent.
      </label>
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
      <Button type="submit" disabled={pending || !authorised || preview.length === 0}>
        {pending ? "Starting…" : "Run assessment"}
      </Button>
    </form>
  );
}
