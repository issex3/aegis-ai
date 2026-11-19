"use client";

import Link from "next/link";
import { NumberTicker } from "@/components/motion/number-ticker";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { Kicker, Panel } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CountChart } from "@/components/charts";
import { formatWhen, titleCase } from "@/lib/labels";
import type { DashboardSummary, Programme } from "@/lib/types";
import { countEntries, showAssessmentChart, showSeverityChart } from "@/lib/dashboard";

export function OverviewClient({
  summary,
  programmes,
  activity,
  needsAgents,
  needsProgramme,
}: {
  summary: DashboardSummary;
  programmes: Programme[];
  activity: boolean;
  needsAgents: boolean;
  needsProgramme: boolean;
}) {
  const running = programmes.filter((p) => p.status === "running" || p.status === "queued");
  const recentProgrammes = programmes.slice(0, 5);

  return (
    <div>
      <Reveal>
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Kicker>Investigate</Kicker>
            <h1 className="mt-2 font-display text-[32px] leading-[1.02] tracking-[-0.04em] sm:text-[40px]">Overview</h1>
            <p className="mt-2 max-w-xl text-[13px] leading-6 text-muted-foreground">
              Operations brief — next actions, programmes, and open evidence from live records.
            </p>
          </div>
          {needsAgents ? (
            <Button asChild>
              <Link href="/agents/new">Register an agent</Link>
            </Button>
          ) : needsProgramme ? (
            <Button asChild>
              <Link href="/programmes/new">Create a programme</Link>
            </Button>
          ) : (
            <Button asChild>
              <Link href="/sandboxes">Open Simulation Lab</Link>
            </Button>
          )}
        </div>
      </Reveal>

      {(needsAgents || needsProgramme) && !activity ? (
        <Reveal delay={0.05}>
          <Panel className="relative mb-6 overflow-hidden">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(600px_200px_at_10%_0%,rgba(91,141,239,0.16),transparent)]" />
            <div className="relative">
            <Kicker className="text-signal">Getting started</Kicker>
            <h2 className="mt-2 text-[18px] font-medium tracking-tight">
              {needsAgents ? "Start with an agent" : "Profile agents, then run a programme"}
            </h2>
            <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted-foreground">
              {needsAgents
                ? "Register an agent, capture its profile, then launch a testing programme. Metrics appear only from real records."
                : `${summary.agents.total} agent${summary.agents.total === 1 ? " is" : "s are"} registered. Create a programme to generate findings and reports.`}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {needsAgents ? (
                <>
                  <Button asChild>
                    <Link href="/onboarding">Continue onboarding</Link>
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href="/agents/new">Register an agent</Link>
                  </Button>
                </>
              ) : (
                <>
                  <Button asChild>
                    <Link href="/programmes/new">Create a programme</Link>
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href="/agents">Review agents</Link>
                  </Button>
                </>
              )}
            </div>
            </div>
          </Panel>
        </Reveal>
      ) : null}

      <Stagger className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        <StaggerItem>
          <MetricCard label="Agents" value={summary.agents.total} hint={`${summary.agents.active} active`} />
        </StaggerItem>
        <StaggerItem>
          <MetricCard label="Programmes" value={programmes.length} hint={running.length ? `${running.length} running` : "None running"} />
        </StaggerItem>
        <StaggerItem>
          <MetricCard label="Open findings" value={summary.findings.open} hint={`${summary.findings.total} total`} />
        </StaggerItem>
        <StaggerItem>
          <MetricCard label="Assessments" value={summary.assessments.total} hint="Including programme runs" />
        </StaggerItem>
      </Stagger>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Reveal delay={0.1}>
          <Panel padded={false} className="overflow-hidden">
            <div className="border-b border-border px-4 py-3">
              <Kicker>Next actions</Kicker>
              <h2 className="mt-1 text-[15px] font-medium">Journey</h2>
            </div>
            <ol className="divide-y divide-border">
              {[
                { step: "01", label: "Register agent", href: "/agents/new", done: summary.agents.total > 0 },
                { step: "02", label: "Complete profile", href: "/agents", done: summary.agents.total > 0 },
                { step: "03", label: "Launch programme", href: "/programmes", done: programmes.length > 0 },
                { step: "04", label: "Review findings", href: "/findings", done: summary.findings.total > 0 },
              ].map((item) => (
                <li key={item.step}>
                  <Link
                    href={item.href}
                    className="group flex items-center gap-3 px-4 py-3 text-[13px] transition-colors hover:bg-white/[0.03]"
                  >
                    <span className="font-mono text-[10px] text-faint">{item.step}</span>
                    <span className={item.done ? "text-muted-foreground line-through" : "text-foreground"}>{item.label}</span>
                    <span className="ml-auto text-meta transition-transform group-hover:translate-x-0.5">{item.done ? "Done" : "Open →"}</span>
                  </Link>
                </li>
              ))}
            </ol>
          </Panel>
        </Reveal>

        <Reveal delay={0.14}>
          <Panel padded={false} className="overflow-hidden">
            <div className="border-b border-border px-4 py-3">
              <Kicker>Evidence</Kicker>
              <h2 className="mt-1 text-[15px] font-medium">Open findings</h2>
            </div>
            {summary.findings.open === 0 ? (
              <p className="px-4 py-6 text-[13px] text-muted-foreground">No open findings yet.</p>
            ) : (
              <div className="divide-y divide-border">
                {countEntries(summary.findings.by_severity).map((item) => (
                  <Link
                    key={item.name}
                    href="/findings"
                    className="flex items-center justify-between px-4 py-3 text-[13px] hover:bg-white/[0.03]"
                  >
                    <span>{titleCase(item.name)}</span>
                    <span className="tabular text-foreground">{item.count}</span>
                  </Link>
                ))}
              </div>
            )}
          </Panel>
        </Reveal>
      </div>

      {recentProgrammes.length > 0 ? (
        <Reveal delay={0.16}>
          <Panel className="mt-5" padded={false}>
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <Kicker>Test</Kicker>
                <h2 className="mt-1 text-[15px] font-medium">Programmes</h2>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/programmes">All programmes</Link>
              </Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Programme</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentProgrammes.map((programme) => (
                  <TableRow key={programme.id}>
                    <TableCell>
                      <Link href={`/programmes/${programme.id}`} className="hover:text-signal">
                        {programme.industry_name} · {programme.agent_name}
                      </Link>
                    </TableCell>
                    <TableCell>{titleCase(programme.status)}</TableCell>
                    <TableCell>{formatWhen(programme.updated_at ?? programme.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Panel>
        </Reveal>
      ) : null}

      {activity ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {summary.posture ? (
            <Reveal delay={0.18}>
              <Panel className="lg:col-span-2">
                <Kicker>Posture</Kicker>
                <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <p className="text-metric">
                      {summary.posture.score === null ? "—" : <NumberTicker value={summary.posture.score} />}
                    </p>
                    <p className="mt-1 text-[13px] text-muted-foreground">
                      {titleCase(summary.posture.classification)} · coverage {Math.round(summary.posture.coverage * 100)}% · confidence{" "}
                      {Math.round(summary.posture.confidence * 100)}%
                    </p>
                  </div>
                  <p className="max-w-md text-[13px] text-muted-foreground">{summary.posture.disclaimer}</p>
                </div>
              </Panel>
            </Reveal>
          ) : null}
          <Reveal delay={0.2}>
            <Panel>
              <h2 className="text-[13px] font-medium">Assessments by status</h2>
              <p className="mt-1 text-meta">{summary.assessments.total} total</p>
              {showAssessmentChart(summary) ? (
                <CountChart data={countEntries(summary.assessments.by_status).map((item) => ({ ...item, name: titleCase(item.name) }))} />
              ) : null}
            </Panel>
          </Reveal>
          <Reveal delay={0.22}>
            <Panel>
              <h2 className="text-[13px] font-medium">Findings by severity</h2>
              <p className="mt-1 text-meta">
                {summary.findings.open} open of {summary.findings.total}
              </p>
              {showSeverityChart(summary) ? (
                <CountChart data={countEntries(summary.findings.by_severity).map((item) => ({ ...item, name: titleCase(item.name) }))} />
              ) : (
                <p className="mt-6 text-[13px] text-muted-foreground">No findings recorded.</p>
              )}
            </Panel>
          </Reveal>
        </div>
      ) : null}

      {summary.recent_assessments.length > 0 ? (
        <Reveal delay={0.24}>
          <Panel className="mt-5" padded={false}>
            <div className="border-b border-border px-4 py-3">
              <Kicker>Recent</Kicker>
              <h2 className="mt-1 text-[15px] font-medium">Assessments</h2>
            </div>
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
                {summary.recent_assessments.map((assessment) => (
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
          </Panel>
        </Reveal>
      ) : null}
    </div>
  );
}

function MetricCard({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div className="surface rounded-md px-4 py-3.5">
      <Kicker>{label}</Kicker>
      <p className="mt-2.5 text-metric">
        <NumberTicker value={value} />
      </p>
      <p className="mt-1.5 text-meta">{hint}</p>
    </div>
  );
}
