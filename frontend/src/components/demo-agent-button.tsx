"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import type { Agent } from "@/lib/types";

export function DemoAgentButton() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function create() {
    setPending(true);
    setMessage(null);
    const result = await clientApi<Agent>("/agents/demo", { method: "POST" });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.push(`/agents/${result.data.id}`);
    router.refresh();
  }

  return (
    <div>
      <Button variant="outline" onClick={create} disabled={pending}>
        {pending ? "Adding…" : "Add demo agent"}
      </Button>
      {message ? <p className="mt-2 text-sm text-destructive">{message}</p> : null}
    </div>
  );
}
