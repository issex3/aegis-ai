import type { Metadata } from "next";
import Link from "next/link";
import { BuildProgrammeButton } from "@/components/intel/build-programme-button";
import { Kicker, Panel, SectionHeader } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { serverApi } from "@/lib/api";
import { formatWhen, integrationLabel, titleCase } from "@/lib/labels";
import type { Agent, AgentProfile, LibraryIndex, Programme } from "@/lib/types";

export const metadata: Metadata = { title: "Programmes" };

const steps = [
  { title: "Profile", body: "Describe the agent's industry, responsibilities, tools, permissions, and data." },
  { title: "Select", body: "Aegis maps capabilities to threats, ranks applicable scenarios, and explains every exclusion." },
  { title: "Execute", body: "Each scenario runs as a simulated workflow against a synthetic sandbox, in the background." },
  { title: "Report", body: "Industry score, threat breakdown, evidence, remediation, and comparison with the last run." },
];

export default async function ProgrammesPage() {
  const [programmes, agents, index] = await Promise.all([
    serverApi<Programme[]>("/programmes"),
    serverApi<Agent[]>("/agents"),
    serverApi<LibraryIndex>("/scenario-library"),
  ]);
  const active = agents.filter((agent) => agent.status === "active");
  const profiles = await Promise.all(active.map((agent) => serverApi<{ profile: AgentProfile | null }>(`/agents/${agent.id}/profile`)));
  const industryNames = Object.fromEntries(index.industries.map((item) => [item.slug, item.name]));

  return (
    <div>
      <SectionHeader
        kicker="Industry intelligence"
        title="Testing programmes"
        description="Tailored testing built from what each agent actually does, not from a generic checklist."
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/library">Browse the scenario library</Link>
          </Button>
        }
      />

      <ol className="mb-10 grid border-y border-border md:grid-cols-4">
        {steps.map((step, position) => (
          <li key={step.title} className={`py-5 md:px-5 md:first:pl-0 ${position > 0 ? "border-t border-border md:border-l md:border-t-0" : ""}`}>
            <span className="font-mono text-[11px] text-signal">{String(position + 1).padStart(2, "0")}</span>
            <p className="mt-2 text-[14px] font-medium">{step.title}</p>
            <p className="mt-1 text-[12px] leading-5 text-muted-foreground">{step.body}</p>
          </li>
        ))}
      </ol>

      <section>
        <Kicker>Agents</Kicker>
        {active.length === 0 ? (
          <p className="mt-3 text-[13px] text-muted-foreground">
            No active agents. <Link href="/agents" className="underline underline-offset-4">Add one</Link>, or use the built-in demo agent.
          </p>
        ) : (
          <ul className="mt-3 border-t border-border">
            {active.map((agent, position) => {
              const profile = profiles[position].profile;
              return (
                <li key={agent.id} className="grid gap-3 border-b border-border py-4 md:grid-cols-[minmax(0,1fr)_14rem_auto] md:items-center">
                  <div className="min-w-0">
                    <Link href={`/agents/${agent.id}`} className="truncate text-[14px] hover:text-signal">
                      {agent.name}
                    </Link>
                    <p className="mt-0.5 font-mono text-[11px] text-faint">{integrationLabel(agent.integration_type)}</p>
                  </div>
                  <p className="text-[12px] text-muted-foreground">
                    {profile ? (
                      <>
                        {industryNames[profile.industry] ?? profile.industry} · {profile.capabilities.length} capabilities · v{profile.version}
                      </>
                    ) : (
                      <span className="text-faint">Not profiled</span>
                    )}
                  </p>
                  <div className="flex items-center gap-3 md:justify-end">
                    <Link href={`/agents/${agent.id}/profile`} className="text-[12px] text-muted-foreground underline decoration-input underline-offset-4 hover:text-foreground">
                      {profile ? "Edit profile" : "Profile agent"}
                    </Link>
                    {profile ? <BuildProgrammeButton agentId={agent.id} /> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="mt-12">
        <Kicker>Programmes</Kicker>
        {programmes.length === 0 ? (
          <p className="mt-3 text-[13px] text-muted-foreground">No programmes yet. Profile an agent to build one.</p>
        ) : (
          <Panel className="mt-3 overflow-hidden" padded={false}>
            <div className="hidden grid-cols-[minmax(0,1fr)_10rem_7rem_6rem_9rem] gap-4 border-b border-border bg-inset/60 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint md:grid">
              <span>Agent</span>
              <span>Industry</span>
              <span>Selected</span>
              <span>Runs</span>
              <span>Updated</span>
            </div>
            <ul>
              {programmes.map((programme) => (
                <li key={programme.id} className="border-b border-border/70 last:border-b-0">
                  <Link href={`/programmes/${programme.id}`} className="grid gap-1 px-4 py-3 text-[13px] transition-colors hover:bg-secondary/60 md:grid-cols-[minmax(0,1fr)_10rem_7rem_6rem_9rem] md:items-center md:gap-4">
                    <span className="truncate">
                      {programme.agent_name}
                      <span className="ml-2 font-mono text-[10px] text-faint">{titleCase(programme.intensity)}</span>
                    </span>
                    <span className="text-muted-foreground">{programme.industry_name}</span>
                    <span className="font-mono text-[12px] text-muted-foreground tabular">
                      {programme.stats.selected}/{programme.stats.applicable}
                    </span>
                    <span className="font-mono text-[12px] text-muted-foreground tabular">{programme.runs.length}</span>
                    <span className="font-mono text-[11px] text-faint">{formatWhen(programme.updated_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </section>
    </div>
  );
}
