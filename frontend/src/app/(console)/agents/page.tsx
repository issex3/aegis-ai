import Link from "next/link";
import { DemoAgentButton } from "@/components/demo-agent-button";
import { EmptyState } from "@/components/empty-state";
import { Panel, SectionHeader } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { serverApi } from "@/lib/api";
import { integrationLabel } from "@/lib/labels";
import type { Agent } from "@/lib/types";

export default async function AgentsPage() {
  const agents = await serverApi<Agent[]>("/agents");
  return (
    <div>
      <SectionHeader
        kicker="Registry"
        title="My Agents"
        description="Agents registered to this organisation."
        action={
          <div className="flex flex-wrap gap-2">
            <DemoAgentButton />
            <Button asChild>
              <Link href="/agents/new">Register an agent</Link>
            </Button>
          </div>
        }
      />
      {agents.length === 0 ? (
        <EmptyState
          title="No agents registered"
          body="Add the agent you want to assess. Include its purpose, expected behaviour, and the boundaries it should not cross."
          action={
            <Button asChild>
              <Link href="/agents/new">Register an agent</Link>
            </Button>
          }
        />
      ) : (
        <Panel padded={false}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Integration</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Credential</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents.map((agent) => (
                <TableRow key={agent.id}>
                  <TableCell>
                    <Link href={`/agents/${agent.id}`} className="font-medium hover:text-signal">
                      {agent.name}
                    </Link>
                    <div className="mt-1 max-w-md truncate text-xs text-muted-foreground">{agent.description}</div>
                  </TableCell>
                  <TableCell>{integrationLabel(agent.integration_type)}</TableCell>
                  <TableCell className="font-mono text-xs">{agent.model_name}</TableCell>
                  <TableCell>
                    <Badge tone={agent.status}>{agent.status}</Badge>
                  </TableCell>
                  <TableCell>{agent.credential.configured ? agent.credential.hint : "Not stored"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
      )}
    </div>
  );
}
