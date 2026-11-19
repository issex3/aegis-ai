"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { clientApi } from "@/lib/api";
import type { Agent, Credential } from "@/lib/types";

export function AgentControls({ agent }: { agent: Agent }) {
  const router = useRouter();
  const [credential, setCredential] = useState<Credential>(agent.credential);
  const [secret, setSecret] = useState("");
  const [confirmName, setConfirmName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);

  async function setStatus(status: "active" | "disabled") {
    setMessage(null);
    const result = await clientApi<Agent>(`/agents/${agent.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.refresh();
  }

  async function saveCredential(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    const result = await clientApi<Credential>(`/agents/${agent.id}/credential`, {
      method: "PUT",
      body: JSON.stringify({ secret }),
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setSecret("");
    setCredential(result.data);
    router.refresh();
  }

  async function removeCredential() {
    setMessage(null);
    const result = await clientApi<Credential>(`/agents/${agent.id}/credential`, { method: "DELETE" });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setCredential({ configured: false, hint: null, updated_at: null });
    router.refresh();
  }

  async function removeAgent() {
    setPending(true);
    const result = await clientApi(`/agents/${agent.id}`, { method: "DELETE" });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.push("/agents");
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {agent.status === "active" ? (
          <Button variant="outline" onClick={() => setStatus("disabled")}>
            Disable agent
          </Button>
        ) : (
          <Button variant="outline" onClick={() => setStatus("active")}>
            Enable agent
          </Button>
        )}
        <Button variant="destructive" onClick={() => setOpen(true)}>
          Delete agent
        </Button>
      </div>
      <form onSubmit={saveCredential} className="space-y-3 border border-border p-4">
        <div>
          <h2 className="text-sm font-semibold">Credential</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {credential.configured ? `Stored secret ending ${credential.hint}. The value is not returned to the browser.` : "No credential stored."}
          </p>
        </div>
        <Input type="password" autoComplete="new-password" value={secret} onChange={(event) => setSecret(event.target.value)} placeholder="New secret" />
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={pending || secret.length < 8}>
            {credential.configured ? "Rotate credential" : "Store credential"}
          </Button>
          {credential.configured ? (
            <Button type="button" variant="outline" onClick={removeCredential}>
              Delete credential
            </Button>
          ) : null}
        </div>
      </form>
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogTitle>Delete {agent.name}</DialogTitle>
          <DialogDescription>
            The agent is removed from the workspace and any stored credential is destroyed. Assessment records that already exist stay attached to the organisation.
          </DialogDescription>
          <label className="mt-4 block text-sm" htmlFor="confirm-name">
            Type the agent name to confirm
          </label>
          <Input id="confirm-name" className="mt-2" value={confirmName} onChange={(event) => setConfirmName(event.target.value)} />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={confirmName !== agent.name || pending} onClick={removeAgent}>
              Delete agent
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
