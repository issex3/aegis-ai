import { OverviewClient } from "@/components/dashboard/overview-client";
import { serverApi } from "@/lib/api";
import { hasAssessmentActivity } from "@/lib/dashboard";
import type { DashboardSummary, Programme } from "@/lib/types";

export default async function DashboardPage() {
  const [summary, programmes] = await Promise.all([
    serverApi<DashboardSummary>("/dashboard"),
    serverApi<Programme[]>("/programmes").catch(() => [] as Programme[]),
  ]);
  const activity = hasAssessmentActivity(summary);
  const needsAgents = summary.agents.total === 0;
  const needsProgramme = !needsAgents && programmes.length === 0;

  return (
    <OverviewClient
      summary={summary}
      programmes={programmes}
      activity={activity}
      needsAgents={needsAgents}
      needsProgramme={needsProgramme}
    />
  );
}
