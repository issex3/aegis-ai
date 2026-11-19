import Link from "next/link";
import { notFound } from "next/navigation";
import { AgentControls } from "@/components/agent-controls";
import { ConnectionTest } from "@/components/connection-test";
import { DemoProfileControl } from "@/components/demo-profile-control";
import { AgentForm } from "@/components/agent-form";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiNotFound, serverApi } from "@/lib/api";
import { formatWhen, titleCase } from "@/lib/labels";
import type { Agent, AgentProfile, Assessment } from "@/lib/types";
import { BuildProgrammeButton } from "@/components/intel/build-programme-button";

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let agent: Agent;
  try {
    agent = await serverApi<Agent>(`/agents/${id}`);
  } catch (error) {
    if (error instanceof ApiNotFound) notFound();
    throw error;
  }
  const [assessments, { profile }] = await Promise.all([
    serverApi<Assessment[]>(`/agents/${id}/assessments`),
    serverApi<{ profile: AgentProfile | null }>(`/agents/${id}/profile`),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Agent"
        title={agent.name}
        description={agent.description}
        action={<Badge tone={agent.status}>{agent.status}</Badge>}
      />
      <Card className="mb-4 flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">Security profile</p>
          {profile ? (
            <p className="mt-1.5 text-sm text-muted-foreground">
              {titleCase(profile.industry)} · {profile.capabilities.length} confirmed capabilities · {profile.risk_sensitivity} sensitivity · v{profile.version}
            </p>
          ) : (
            <p className="mt-1.5 text-sm text-muted-foreground">Profile this agent to receive industry-specific scenarios chosen from what it actually does.</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link href={`/agents/${agent.id}/profile`} className="text-sm text-muted-foreground underline decoration-input underline-offset-4 hover:text-foreground">
            {profile ? "Edit profile" : "Profile agent"}
          </Link>
          {profile ? <BuildProgrammeButton agentId={agent.id} label="Build testing programme" /> : null}
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Details</h2>
          <AgentForm agent={agent} />
        </Card>
        <Card className="space-y-4 p-5">
          <ConnectionTest agentId={agent.id} adapterStatus={agent.adapter_status} />
          <AgentControls agent={agent} />
          {agent.demo_profile ? (
            <div className="border-t border-border pt-4">
              <DemoProfileControl agentId={agent.id} current={agent.demo_profile} />
            </div>
          ) : null}
        </Card>
      </div>
      <Card>
        <div className="flex items-center justify-between border-b border-border px-3 py-3">
          <h2 className="text-sm font-semibold">Assessment history</h2>
          <Link href="/assessments" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            All assessments
          </Link>
        </div>
        {assessments.length === 0 ? (
          <p className="px-3 py-6 text-sm text-muted-foreground">No assessments have been recorded for this agent.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assessments.map((assessment) => (
                <TableRow key={assessment.id}>
                  <TableCell>{assessment.name}</TableCell>
                  <TableCell>{titleCase(assessment.status)}</TableCell>
                  <TableCell>{formatWhen(assessment.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
