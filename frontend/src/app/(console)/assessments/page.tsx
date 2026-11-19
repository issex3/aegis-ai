import Link from "next/link";
import { AssessmentWizard } from "@/components/assessment-wizard";
import { EmptyState } from "@/components/empty-state";
import { Kicker, Panel, SectionHeader } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { serverApi } from "@/lib/api";
import { formatWhen, titleCase } from "@/lib/labels";
import type { Agent, Assessment, Sandbox } from "@/lib/types";

export default async function AssessmentsPage() {
  const [assessments, agents, sandboxes] = await Promise.all([
    serverApi<Assessment[]>("/assessments"),
    serverApi<Agent[]>("/agents"),
    serverApi<Sandbox[]>("/sandboxes"),
  ]);
  return (
    <div>
      <SectionHeader
        kicker="Testing"
        title="Assessments"
        description="Programmes are the primary path. Manual catalogue runs remain available when you need a one-off."
      />
      {agents.length === 0 ? (
        <EmptyState
          title="Register an agent first"
          body="Use the built-in demo agent if you do not have an external API key."
          action={
            <Button asChild>
              <Link href="/agents">Go to agents</Link>
            </Button>
          }
        />
      ) : (
        <>
          <Panel className="mb-6 border-signal/30">
            <Kicker className="text-signal">Primary path</Kicker>
            <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0 max-w-2xl">
                <h2 className="text-[15px] font-medium">Build a testing programme</h2>
                <p className="mt-1 text-[13px] leading-6 text-muted-foreground">
                  Profile the agent, then run tailored scenarios from its industry, responsibilities, and permissions — with an industry score and comparison to the previous run.
                </p>
              </div>
              <Button asChild>
                <Link href="/programmes">Open programmes</Link>
              </Button>
            </div>
          </Panel>

          <details className="mb-6 border border-border bg-panel/80 open:[&_summary_.hint]:hidden">
            <summary className="cursor-pointer list-none px-5 py-4 marker:content-none [&::-webkit-details-marker]:hidden">
              <Kicker>Secondary</Kicker>
              <div className="mt-1 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-[15px] font-medium">Manual catalogue run</h2>
                <span className="hint text-meta">Expand to configure →</span>
              </div>
              <p className="mt-1 max-w-2xl text-[13px] text-muted-foreground">
                Choose an agent, a sandbox, and categories for a one-off assessment outside a programme.
              </p>
            </summary>
            <div className="border-t border-border px-5 py-4">
              <AssessmentWizard agents={agents} sandboxes={sandboxes} />
            </div>
          </details>
        </>
      )}

      <Panel padded={false}>
        <div className="border-b border-border px-4 py-3">
          <Kicker>History</Kicker>
          <h2 className="mt-1 text-[15px] font-medium">Assessments</h2>
        </div>
        {assessments.length === 0 ? (
          <p className="px-4 py-6 text-[13px] text-muted-foreground">No assessments have been created.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assessments.map((assessment) => (
                <TableRow key={assessment.id}>
                  <TableCell>
                    <Link href={`/assessments/${assessment.id}`} className="hover:text-signal">
                      {assessment.name}
                    </Link>
                  </TableCell>
                  <TableCell>{assessment.agent_name}</TableCell>
                  <TableCell>{titleCase(assessment.status)}</TableCell>
                  <TableCell>{formatWhen(assessment.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
    </div>
  );
}
