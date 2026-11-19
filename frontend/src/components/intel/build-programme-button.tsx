"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import type { Programme } from "@/lib/types";

export function BuildProgrammeButton({ agentId, label = "Build programme" }: { agentId: string; label?: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function build() {
    setPending(true);
    const result = await clientApi<Programme>("/programmes", { method: "POST", body: JSON.stringify({ agent_id: agentId, intensity: "standard" }) });
    setPending(false);
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    router.push(`/programmes/${result.data.id}`);
  }

  return (
    <Button size="sm" onClick={build} disabled={pending}>
      {pending ? "Building…" : label}
    </Button>
  );
}
