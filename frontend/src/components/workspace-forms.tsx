"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field } from "@/components/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clientApi, fieldErrors } from "@/lib/api";
import type { Agent, Assessment, Consent, Session } from "@/lib/types";

export function DraftAssessmentForm({ agents }: { agents: Agent[] }) {
  const router = useRouter();
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [name, setName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const activeAgents = agents.filter((agent) => agent.status === "active");

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    const result = await clientApi<Assessment>("/assessments", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, name }),
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setName("");
    router.refresh();
  }

  if (activeAgents.length === 0) return null;

  return (
    <form onSubmit={onSubmit} className="mt-6 grid gap-4 border border-border p-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
      <Field label="Assessment name" htmlFor="assessment-name">
        <Input id="assessment-name" value={name} onChange={(event) => setName(event.target.value)} required />
      </Field>
      <Field label="Agent" htmlFor="assessment-agent">
        <select id="assessment-agent" className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={agentId} onChange={(event) => setAgentId(event.target.value)}>
          {activeAgents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>
      </Field>
      <Button type="submit" disabled={pending}>
        {pending ? "Saving…" : "Save draft"}
      </Button>
      {message ? <p className="text-sm text-destructive md:col-span-3">{message}</p> : null}
    </form>
  );
}

export function ConsentForm({ consent, canManage }: { consent: Consent; canManage: boolean }) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function update(granted: boolean) {
    setPending(true);
    setMessage(null);
    const result = await clientApi<Consent>("/intelligence/consent", {
      method: "POST",
      body: JSON.stringify({
        granted,
        permitted_categories: granted ? ["prompt_injection", "sensitive_data_leakage", "unauthorised_tool_use", "cross_user_exposure", "privilege_escalation", "data_exfiltration", "instruction_hierarchy", "unsafe_output", "insecure_workflow"] : [],
        intended_use: granted ? "Evaluation statistics after human review. Customer replies are not included." : "Withdrawn.",
      }),
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <div className="mt-4 space-y-3">
      <p className="text-sm text-muted-foreground">
        {`Current decision: ${consent.granted ? "contribution allowed" : "contribution not allowed"}${consent.recorded_at ? ` · policy ${consent.policy_version}` : ""}. Each change is stored as its own record.`}
      </p>
      {canManage ? (
        <div className="flex flex-wrap gap-2">
          <Button disabled={pending || consent.granted} onClick={() => update(true)}>
            Allow contribution
          </Button>
          <Button variant="outline" disabled={pending || !consent.granted} onClick={() => update(false)}>
            Withdraw consent
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Only an owner or admin can change contribution consent.</p>
      )}
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
    </div>
  );
}

export function SettingsForms({ session }: { session: Session }) {
  const router = useRouter();
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordOk, setPasswordOk] = useState(false);
  const [orgError, setOrgError] = useState<string | null>(null);
  const canManage = session.role === "owner" || session.role === "admin";

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileError(null);
    const form = new FormData(event.currentTarget);
    const result = await clientApi("/settings/profile", {
      method: "PATCH",
      body: JSON.stringify({ full_name: form.get("full_name") }),
    });
    if (!result.ok) {
      const fields = fieldErrors(result.error);
      setProfileError(fields.full_name || result.error.error.message);
      return;
    }
    router.refresh();
  }

  async function savePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordOk(false);
    const form = new FormData(event.currentTarget);
    const result = await clientApi("/settings/password", {
      method: "PATCH",
      body: JSON.stringify({
        current_password: form.get("current_password"),
        new_password: form.get("new_password"),
      }),
    });
    if (!result.ok) {
      setPasswordError(result.error.error.message);
      return;
    }
    event.currentTarget.reset();
    setPasswordOk(true);
  }

  async function saveOrganisation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOrgError(null);
    const form = new FormData(event.currentTarget);
    const result = await clientApi("/settings/organisation", {
      method: "PATCH",
      body: JSON.stringify({ name: form.get("name") }),
    });
    if (!result.ok) {
      setOrgError(result.error.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <div className="grid gap-4">
      <form onSubmit={saveProfile} className="space-y-3 border border-border p-4">
        <h2 className="text-sm font-semibold">Profile</h2>
        <Field label="Full name" htmlFor="full_name">
          <Input id="full_name" name="full_name" defaultValue={session.user.full_name} required />
        </Field>
        <p className="text-sm text-muted-foreground">{session.user.email}</p>
        {profileError ? <p className="text-sm text-destructive">{profileError}</p> : null}
        <Button type="submit">Save profile</Button>
      </form>
      <form onSubmit={savePassword} className="space-y-3 border border-border p-4">
        <h2 className="text-sm font-semibold">Password</h2>
        <Field label="Current password" htmlFor="current_password">
          <Input id="current_password" name="current_password" type="password" autoComplete="current-password" required />
        </Field>
        <Field label="New password" htmlFor="new_password" hint="At least 12 characters, with a letter and a number.">
          <Input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={12} />
        </Field>
        {passwordError ? <p className="text-sm text-destructive">{passwordError}</p> : null}
        {passwordOk ? <p className="text-sm text-success">Password updated.</p> : null}
        <Button type="submit">Change password</Button>
      </form>
      <form onSubmit={saveOrganisation} className="space-y-3 border border-border p-4">
        <h2 className="text-sm font-semibold">Organisation</h2>
        <Field label="Name" htmlFor="organisation-name">
          <Input id="organisation-name" name="name" defaultValue={session.organisation.name} required disabled={!canManage} />
        </Field>
        <p className="text-sm text-muted-foreground">Slug {session.organisation.slug}</p>
        {orgError ? <p className="text-sm text-destructive">{orgError}</p> : null}
        {canManage ? <Button type="submit">Save organisation</Button> : <p className="text-sm text-muted-foreground">Only an owner or admin can rename the organisation.</p>}
      </form>
      <MfaSettings enabled={Boolean(session.user.mfa_enabled)} />
    </div>
  );
}

function MfaSettings({ enabled }: { enabled: boolean }) {
  const router = useRouter();
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function start() {
    const result = await clientApi<{ secret: string; otpauth_url: string }>("/auth/mfa/setup", { method: "POST" });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setSecret(result.data.secret);
    setUri(result.data.otpauth_url);
    setMessage(null);
  }

  async function confirm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await clientApi<{ enabled: boolean; recovery_codes: string[] }>("/auth/mfa/confirm", {
      method: "POST",
      body: JSON.stringify({ code: form.get("code") }),
    });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setRecovery(result.data.recovery_codes);
    setSecret(null);
    router.refresh();
  }

  return (
    <div className="space-y-3 border border-border p-4">
      <h2 className="text-sm font-semibold">Multi-factor authentication</h2>
      <p className="text-sm text-muted-foreground">{enabled ? "Authenticator MFA is enabled for this account." : "Add an authenticator app. Production administrators must enable MFA before privileged actions."}</p>
      {!enabled && !secret ? (
        <Button type="button" onClick={start}>
          Start MFA setup
        </Button>
      ) : null}
      {secret ? (
        <form onSubmit={confirm} className="space-y-3">
          <p className="break-all font-mono text-xs">{uri}</p>
          <p className="text-sm text-muted-foreground">Secret {secret}</p>
          <Field label="Authentication code" htmlFor="mfa-code">
            <Input id="mfa-code" name="code" inputMode="numeric" required />
          </Field>
          <Button type="submit">Confirm MFA</Button>
        </form>
      ) : null}
      {recovery ? (
        <div>
          <p className="text-sm">Store these recovery codes. They are shown once.</p>
          <ul className="mt-2 font-mono text-xs">
            {recovery.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
    </div>
  );
}
