import Link from "next/link";
import { AssessmentProgress } from "@/components/assessment-progress";
import { ProgrammeRun } from "@/components/intel/programme-run";
import { PageHeader } from "@/components/page-header";
import { serverApi } from "@/lib/api";
import type { AssessmentDetail } from "@/lib/types";

export default async function AssessmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await serverApi<AssessmentDetail>(`/assessments/${id}`);
  const programme = detail.engine === "scenario";
  return (
    <div>
      <PageHeader
        kicker={programme ? `Programme run${detail.is_simulated ? " · simulated" : ""}` : detail.is_simulated ? "Simulated assessment" : "Assessment"}
        title={detail.name}
        description={
          detail.is_simulated
            ? "These results come from the local demo agent. They are not an external model."
            : programme
              ? "Each scenario ran as a simulated workflow. Outcomes are based on the agent's replies, tool requests, and sandbox state."
              : "Outcomes are based on the observable response and tool calls."
        }
        action={
          <Link href="/findings" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            Findings
          </Link>
        }
      />
      {programme ? <ProgrammeRun initial={detail} /> : <AssessmentProgress initial={detail} />}
    </div>
  );
}
