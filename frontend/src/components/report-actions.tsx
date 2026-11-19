"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import { toast } from "sonner";

export function GenerateReportButton({ assessmentId }: { assessmentId: string }) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function generate() {
    setPending(true);
    setMessage(null);
    const result = await clientApi<{ id: string }>(`/assessments/${assessmentId}/reports`, { method: "POST" });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.error.message);
      toast.error(result.error.error.message);
      return;
    }
    toast.success("Report ready. The download should start now.");
    const link = document.createElement("a");
    link.href = `/api/v1/reports/${result.data.id}/download`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    router.refresh();
  }

  return (
    <div>
      <Button onClick={generate} disabled={pending}>
        {pending ? "Generating…" : "Generate PDF"}
      </Button>
      {message ? <p className="mt-2 text-sm text-destructive">{message}</p> : null}
    </div>
  );
}

export function ReportRowActions({ reportId }: { reportId: string }) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);

  async function regenerate() {
    const result = await clientApi(`/reports/${reportId}/regenerate`, { method: "POST" });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.refresh();
  }

  async function remove() {
    const result = await clientApi(`/reports/${reportId}`, { method: "DELETE" });
    if (!result.ok) {
      setMessage(result.error.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <div className="flex flex-wrap gap-2">
      <a className="text-sm underline underline-offset-4" href={`/api/v1/reports/${reportId}/download`}>
        Download
      </a>
      <button className="text-sm underline underline-offset-4" onClick={regenerate}>
        Regenerate
      </button>
      <button className="text-sm underline underline-offset-4" onClick={remove}>
        Delete
      </button>
      {message ? <span className="text-sm text-destructive">{message}</span> : null}
    </div>
  );
}
