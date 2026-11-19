"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { GenerateReportButton } from "@/components/report-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import { titleCase } from "@/lib/labels";
import type { AssessmentDetail } from "@/lib/types";

const active = new Set(["pending", "running"]);

export function AssessmentProgress({ initial }: { initial: AssessmentDetail }) {
  const router = useRouter();
  const [detail, setDetail] = useState(initial);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    if (!active.has(detail.status)) return;
    const timer = window.setInterval(async () => {
      const result = await clientApi<AssessmentDetail>(`/assessments/${detail.id}`);
      if (result.ok) setDetail(result.data);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [detail.id, detail.status]);

  async function cancel() {
    const result = await clientApi<AssessmentDetail>(`/assessments/${detail.id}/cancel`, { method: "POST" });
    if (result.ok) {
      setDetail(result.data);
      router.refresh();
    }
  }

  return (
    <div className="space-y-4">
      {detail.score ? (
        <p className="text-sm text-muted-foreground">
          Internal score {detail.score.score === null ? "not scored" : `${detail.score.score} (${detail.score.classification})`}. Applicable tests {detail.score.applicable_tests}. Inconclusive {detail.score.inconclusive}. {detail.score.disclaimer}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={detail.status}>{titleCase(detail.status)}</Badge>
        {detail.is_simulated ? <Badge tone="medium">Simulated</Badge> : null}
        {detail.simulated_role ? <span className="text-sm text-muted-foreground">Role {detail.simulated_role}</span> : null}
        {detail.status === "completed" ? <GenerateReportButton assessmentId={detail.id} /> : null}
        {active.has(detail.status) ? (
          <Button variant="outline" size="sm" onClick={cancel}>
            Cancel
          </Button>
        ) : null}
      </div>
      {detail.error_summary ? <p className="text-sm text-destructive">{detail.error_summary}</p> : null}
      <div className="space-y-2">
        {detail.results.map((result) => (
          <article key={result.id} className="border border-border">
            <button className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left" onClick={() => setOpen(open === result.id ? null : result.id)}>
              <span>
                <span className="block text-sm">{result.title}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{result.summary}</span>
              </span>
              <span className="shrink-0 text-right">
                <Badge tone={result.outcome === "FAIL" ? "high" : result.outcome === "PASS" ? "active" : "neutral"}>{result.outcome}</Badge>
                <span className="mt-1 block font-mono text-[11px] text-muted-foreground">{result.duration_ms ?? 0} ms</span>
              </span>
            </button>
            {open === result.id ? (
              <div className="space-y-3 border-t border-border px-3 py-3 text-sm">
                <p className="text-muted-foreground">Input</p>
                <pre className="whitespace-pre-wrap font-mono text-xs">{result.evidence.input}</pre>
                <p className="text-muted-foreground">Observable response</p>
                <pre className="whitespace-pre-wrap font-mono text-xs">{result.evidence.observable_response || "—"}</pre>
                {result.evidence.tool_calls && result.evidence.tool_calls.length > 0 ? (
                  <>
                    <p className="text-muted-foreground">Tool calls</p>
                    <ul className="space-y-1 font-mono text-xs">
                      {result.evidence.sandbox_tool_events?.map((event, index) => (
                        <li key={`${event.tool}-${index}`}>
                          {event.tool} · {event.allowed ? "allowed" : "denied"} · {event.role} · {event.policy}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
                {result.evidence.limitations?.map((item) => (
                  <p key={item} className="text-xs text-muted-foreground">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}
