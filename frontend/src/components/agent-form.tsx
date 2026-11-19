"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field } from "@/components/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { clientApi, fieldErrors } from "@/lib/api";
import { integrationTypes } from "@/lib/labels";
import type { Agent } from "@/lib/types";

const empty = {
  name: "",
  description: "",
  integration_type: "openai_compatible",
  api_endpoint: "",
  model_name: "",
  purpose: "",
  behaviour: "",
  security_boundaries: "",
  secret: "",
  timeout_seconds: "30",
  max_output_tokens: "512",
  temperature: "",
};

export function AgentForm({ agent }: { agent?: Agent }) {
  const router = useRouter();
  const [values, setValues] = useState({
    ...empty,
    ...(agent
      ? {
          name: agent.name,
          description: agent.description,
          integration_type: agent.integration_type,
          api_endpoint: agent.api_endpoint,
          model_name: agent.model_name,
          purpose: agent.purpose,
          behaviour: agent.behaviour,
          security_boundaries: agent.security_boundaries,
          secret: "",
          timeout_seconds: String(agent.timeout_seconds ?? 30),
          max_output_tokens: String(agent.max_output_tokens ?? 512),
          temperature: agent.temperature === null || agent.temperature === undefined ? "" : String(agent.temperature),
        }
      : {}),
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function set(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    setErrors({});
    const payload: Record<string, string | number | null> = {
      ...values,
      timeout_seconds: Number(values.timeout_seconds),
      max_output_tokens: Number(values.max_output_tokens),
      temperature: values.temperature === "" ? null : Number(values.temperature),
    };
    if (agent) payload.secret = null;
    else if (!payload.secret) payload.secret = null;
    const result = await clientApi<Agent>(agent ? `/agents/${agent.id}` : "/agents", {
      method: agent ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      setErrors(fieldErrors(result.error));
      return;
    }
    if (!agent) setValues((current) => ({ ...current, secret: "" }));
    router.push(`/agents/${result.data.id}`);
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Name" htmlFor="name" error={errors.name}>
          <Input id="name" value={values.name} onChange={(event) => set("name", event.target.value)} required />
        </Field>
        <Field label="Model" htmlFor="model_name" error={errors.model_name}>
          <Input id="model_name" value={values.model_name} onChange={(event) => set("model_name", event.target.value)} required />
        </Field>
      </div>
      <Field label="Description" htmlFor="description" error={errors.description}>
        <Textarea id="description" value={values.description} onChange={(event) => set("description", event.target.value)} required />
      </Field>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Integration type" htmlFor="integration_type" error={errors.integration_type}>
          <select
            id="integration_type"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={values.integration_type}
            onChange={(event) => set("integration_type", event.target.value)}
          >
            {integrationTypes.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="API endpoint" htmlFor="api_endpoint" error={errors.api_endpoint} hint="HTTPS, or localhost for a development agent.">
          <Input id="api_endpoint" value={values.api_endpoint} onChange={(event) => set("api_endpoint", event.target.value)} required />
        </Field>
      </div>
      <Field label="Intended purpose" htmlFor="purpose" error={errors.purpose}>
        <Textarea id="purpose" value={values.purpose} onChange={(event) => set("purpose", event.target.value)} required />
      </Field>
      <Field label="Expected behaviour" htmlFor="behaviour" error={errors.behaviour}>
        <Textarea id="behaviour" value={values.behaviour} onChange={(event) => set("behaviour", event.target.value)} required />
      </Field>
      <Field label="Security boundaries" htmlFor="security_boundaries" error={errors.security_boundaries}>
        <Textarea id="security_boundaries" value={values.security_boundaries} onChange={(event) => set("security_boundaries", event.target.value)} required />
      </Field>
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Timeout seconds" htmlFor="timeout_seconds">
          <Input id="timeout_seconds" type="number" min={5} max={60} value={values.timeout_seconds} onChange={(event) => set("timeout_seconds", event.target.value)} />
        </Field>
        <Field label="Max output tokens" htmlFor="max_output_tokens">
          <Input id="max_output_tokens" type="number" min={16} max={2048} value={values.max_output_tokens} onChange={(event) => set("max_output_tokens", event.target.value)} />
        </Field>
        <Field label="Temperature" htmlFor="temperature" hint="Leave blank if the endpoint should use its default.">
          <Input id="temperature" type="number" min={0} max={2} step="0.1" value={values.temperature} onChange={(event) => set("temperature", event.target.value)} />
        </Field>
      </div>
      {agent ? null : (
        <Field label="API credential" htmlFor="secret" error={errors.secret} hint="Optional. Stored encrypted on the server and never shown again.">
          <Input id="secret" type="password" autoComplete="new-password" value={values.secret} onChange={(event) => set("secret", event.target.value)} />
        </Field>
      )}
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
      <Button type="submit" disabled={pending}>
        {pending ? "Saving…" : agent ? "Save changes" : "Register agent"}
      </Button>
    </form>
  );
}
