"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";

export function ConnectionTest({ agentId, adapterStatus }: { agentId: string; adapterStatus: string }) {
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function run() {
    setPending(true);
    const result = await clientApi<{ ok: boolean; message: string; simulated: boolean }>(`/agents/${agentId}/connection-test`, { method: "POST" });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    setMessage(result.data.message);
  }

  return (
    <div className="space-y-2">
      <Button variant="outline" onClick={run} disabled={pending || adapterStatus === "not_implemented"}>
        {pending ? "Testing…" : "Test connection"}
      </Button>
      {adapterStatus === "not_implemented" ? <p className="text-sm text-muted-foreground">This adapter is not implemented, so the connection test will not send a request.</p> : null}
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
    </div>
  );
}
