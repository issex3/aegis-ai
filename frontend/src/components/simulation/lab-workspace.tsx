"use client";

import { motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ActivityCharts } from "@/components/simulation/activity-charts";
import { AccountingOverview, AccountingPermissions, AccountingTables } from "@/components/simulation/accounting-panels";
import { DomainOverview, DomainTables } from "@/components/simulation/domain-panels";
import { EventLog } from "@/components/simulation/event-log";
import { PermissionGraph } from "@/components/simulation/permission-graph";
import { ToolConsole } from "@/components/simulation/tool-console";
import { Kicker } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/api";
import { fadeIn, motionSafe } from "@/lib/motion-presets";
import { LAB_IDENTITY, resolveLabKey, type LabEnvironmentKey } from "@/lib/simulation";
import type { LabEvent, LabSession, SandboxDetail } from "@/lib/types";
import { titleCase } from "@/lib/labels";
import { cn } from "@/lib/utils";

type StudioPane = "world" | "instrument" | "trace";

export function LabWorkspace({ sandbox }: { sandbox: SandboxDetail }) {
  const reduce = useReducedMotion();
  const [session, setSession] = useState<LabSession | null>(null);
  const [role, setRole] = useState(sandbox.default_role ?? sandbox.roles?.[0] ?? "");
  const [pane, setPane] = useState<StudioPane>("world");
  const [worldMode, setWorldMode] = useState<"workbench" | "records" | "surface">("workbench");
  const [selectedEvent, setSelectedEvent] = useState<LabEvent | null>(null);
  const [starting, setStarting] = useState(false);
  const [invoking, setInvoking] = useState(false);
  const sessionRef = useRef<LabSession | null>(null);

  const labKey = resolveLabKey({
    slug: sandbox.slug,
    industry_slug: sandbox.industry_slug,
    name: sandbox.name,
    industry_name: sandbox.industry_name ?? "",
  });
  const identity = labKey ? LAB_IDENTITY[labKey] : null;
  const isAccounting = labKey === "accounting";
  const domainKey = labKey && labKey !== "accounting" ? (labKey as Exclude<LabEnvironmentKey, "accounting">) : null;

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  const startSession = useCallback(
    async (nextRole?: string) => {
      setStarting(true);
      const chosen = nextRole ?? role;
      const result = await clientApi<LabSession>(`/sandboxes/${sandbox.id}/lab/sessions`, {
        method: "POST",
        body: JSON.stringify({ role: chosen || null }),
      });
      setStarting(false);
      if (!result.ok) {
        toast.error(result.error.error.message);
        return;
      }
      setSession(result.data);
      setRole(result.data.role);
      setSelectedEvent(null);
      toast.success(`Session started as ${titleCase(result.data.role)}`);
    },
    [role, sandbox.id],
  );

  useEffect(() => {
    return () => {
      const active = sessionRef.current;
      if (!active) return;
      void clientApi(`/sandboxes/${sandbox.id}/lab/sessions/${active.id}`, { method: "DELETE" });
    };
  }, [sandbox.id]);

  async function invokeTool(tool: string, argumentsJson: string) {
    if (!session) return;
    let argumentsPayload: Record<string, unknown> = {};
    try {
      argumentsPayload = JSON.parse(argumentsJson) as Record<string, unknown>;
    } catch {
      toast.error("Arguments must be valid JSON.");
      return;
    }
    setInvoking(true);
    const result = await clientApi<LabSession>(`/sandboxes/${sandbox.id}/lab/sessions/${session.id}/tools`, {
      method: "POST",
      body: JSON.stringify({ tool, arguments: argumentsPayload }),
    });
    setInvoking(false);
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    setSession(result.data);
    setSelectedEvent(result.data.last_event ?? null);
    setPane("trace");
    if (result.data.last_event?.allowed) toast.message(`${tool} allowed`);
    else toast.message(`${tool} denied`);
  }

  async function resetSession() {
    if (!session) return;
    const result = await clientApi<LabSession>(`/sandboxes/${sandbox.id}/lab/sessions/${session.id}/reset`, {
      method: "POST",
    });
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    setSession(result.data);
    setSelectedEvent(null);
    toast.success("Session state reset");
  }

  const scopes = useMemo(() => {
    const value = session?.state?.scopes;
    if (!value || typeof value !== "object") return {} as Record<string, string[]>;
    return value as Record<string, string[]>;
  }, [session]);

  const panes: { id: StudioPane; label: string }[] = [
    { id: "world", label: "World" },
    { id: "instrument", label: "Instrument" },
    { id: "trace", label: "Trace" },
  ];

  function selectEvent(event: LabEvent) {
    setSelectedEvent(event);
    setPane("trace");
  }

  return (
    <div className="space-y-5">
      <section className="surface relative overflow-hidden rounded-lg">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background: `radial-gradient(720px 280px at 12% 0%, color-mix(in oklab, ${identity?.accentVar ?? "var(--signal)"} 22%, transparent), transparent 55%)`,
          }}
        />
        <div className="relative grid gap-4 p-5 lg:grid-cols-[1.45fr_1fr]">
          <div>
            <Kicker>
              {identity?.label ?? sandbox.industry_name ?? "Environment"} · Environment Studio · v{sandbox.version_number ?? "—"}
            </Kicker>
            <h1 className="mt-2 font-display text-[30px] leading-none tracking-[-0.04em] sm:text-[36px]">{sandbox.name}</h1>
            <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted-foreground">{sandbox.description}</p>
            <p className="mt-2 max-w-2xl text-[12px] leading-5 text-faint">{sandbox.boundaries}</p>
          </div>
          <div className="rounded-md border border-border bg-inset/80 p-4 backdrop-blur">
            <Kicker>Session</Kicker>
            <label className="mt-3 block text-[12px] text-muted-foreground">
              Simulated role
              <select
                className="mt-1 h-9 w-full border border-input bg-inset px-3 text-[13px]"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                disabled={Boolean(session)}
              >
                {(sandbox.roles?.length ? sandbox.roles : [sandbox.default_role].filter(Boolean)).map((item) => (
                  <option key={item!} value={item!}>
                    {titleCase(item!)}
                  </option>
                ))}
              </select>
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              {!session ? (
                <Button type="button" onClick={() => startSession()} disabled={starting}>
                  {starting ? "Starting…" : "Enter environment"}
                </Button>
              ) : (
                <>
                  <Button type="button" variant="outline" onClick={resetSession}>
                    Reset state
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={async () => {
                      await clientApi(`/sandboxes/${sandbox.id}/lab/sessions/${session.id}`, { method: "DELETE" });
                      setSession(null);
                      setSelectedEvent(null);
                    }}
                  >
                    End session
                  </Button>
                </>
              )}
            </div>
            {session ? (
              <dl className="mt-4 grid grid-cols-3 gap-2 font-mono text-[11px]">
                <div>
                  <dt className="text-faint">Calls</dt>
                  <dd className="text-foreground tabular">{session.stats.tool_calls}</dd>
                </div>
                <div>
                  <dt className="text-faint">Allowed</dt>
                  <dd className="text-success tabular">{session.stats.allowed}</dd>
                </div>
                <div>
                  <dt className="text-faint">Denied</dt>
                  <dd className="text-destructive tabular">{session.stats.denied}</dd>
                </div>
              </dl>
            ) : (
              <p className="mt-3 text-[12px] text-muted-foreground">Start a session to mutate synthetic state through live sandbox handlers.</p>
            )}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-1 border-b border-border">
        {panes.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setPane(item.id)}
            className={cn(
              "h-9 px-3 text-[13px] transition-colors",
              pane === item.id ? "border-b border-signal text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      <motion.div
        key={pane}
        initial={motionSafe(reduce, fadeIn.initial)}
        animate={fadeIn.animate}
        transition={fadeIn.transition}
        className="space-y-6"
      >
        {pane === "world" ? (
          <>
            <MetaStrip sandbox={sandbox} />
            {!session ? (
              <LockedNotice />
            ) : (
              <>
                <div className="flex flex-wrap gap-1">
                  {(
                    [
                      { id: "workbench" as const, label: "Workbench" },
                      { id: "records" as const, label: "Records" },
                      { id: "surface" as const, label: "Attack surface" },
                    ] as const
                  ).map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setWorldMode(item.id)}
                      className={cn(
                        "h-8 border px-3 text-[12px]",
                        worldMode === item.id ? "border-signal text-foreground" : "border-border text-muted-foreground",
                      )}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                {worldMode === "workbench" ? (
                  isAccounting ? (
                    <AccountingOverview state={session.state} />
                  ) : domainKey ? (
                    <DomainOverview labKey={domainKey} state={session.state} />
                  ) : null
                ) : null}
                {worldMode === "records" ? (
                  isAccounting ? (
                    <AccountingTables state={session.state} />
                  ) : domainKey ? (
                    <DomainTables labKey={domainKey} state={session.state} />
                  ) : (
                    <pre className="overflow-auto border border-border bg-inset p-4 font-mono text-[11px] text-muted-foreground">
                      {JSON.stringify(session.state, null, 2)}
                    </pre>
                  )
                ) : null}
                {worldMode === "surface" ? (
                  <div className="space-y-6">
                    <section>
                      <Kicker className="mb-3">Sensitive data classifications</Kicker>
                      <div className="flex flex-wrap gap-2">
                        {(sandbox.data_classes ?? []).length ? (
                          sandbox.data_classes!.map((item) => (
                            <span key={item.key} className="border border-border px-2 py-1 font-mono text-[11px] text-cyan">
                              {item.label}
                            </span>
                          ))
                        ) : (
                          <span className="text-[13px] text-muted-foreground">No taxonomy data classes bound yet.</span>
                        )}
                      </div>
                    </section>
                    <section>
                      <Kicker className="mb-3">Available scenarios</Kicker>
                      <ul className="divide-y divide-border border border-border">
                        {sandbox.scenarios.map((scenario) => (
                          <li key={scenario.code} className="flex items-center justify-between gap-3 px-4 py-3 text-[13px]">
                            <div>
                              <p className="font-medium">{scenario.title}</p>
                              <p className="mt-0.5 font-mono text-[11px] text-faint">{scenario.code}</p>
                            </div>
                            <span className="font-mono text-[10px] uppercase text-muted-foreground">{scenario.severity}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  </div>
                ) : null}
              </>
            )}
          </>
        ) : null}

        {pane === "instrument" ? (
          session ? (
            <div className="space-y-6">
              {isAccounting ? <AccountingPermissions role={session.role} scopes={scopes} tools={sandbox.tools} /> : null}
              {!isAccounting ? (
                <div className="border border-border bg-inset/40 p-4 text-[13px] text-muted-foreground">
                  Instrument calls the live sandbox handler for role {titleCase(session.role)}. Scope keys:{" "}
                  <span className="font-mono text-foreground">{(scopes[session.role] ?? []).join(", ") || "none"}</span>
                </div>
              ) : null}
              <ToolConsole
                tools={session.tools}
                role={session.role}
                busy={invoking}
                lastEvent={selectedEvent ?? session.last_event}
                onInvoke={invokeTool}
                onInspectEvent={selectEvent}
              />
            </div>
          ) : (
            <LockedNotice />
          )
        ) : null}

        {pane === "trace" ? (
          session ? (
            <div className="space-y-6">
              <section>
                <Kicker className="mb-3">Permission topology</Kicker>
                <PermissionGraph
                  graph={session.graph}
                  highlightTool={selectedEvent?.tool ?? session.last_event?.tool}
                  onSelectTool={(tool) => {
                    const match = [...session.events].reverse().find((event) => event.tool === tool);
                    if (match) selectEvent(match);
                  }}
                />
              </section>
              <section>
                <Kicker className="mb-3">Activity</Kicker>
                <ActivityCharts
                  events={session.events}
                  selectedSequence={selectedEvent?.sequence}
                  onSelectSequence={(sequence) => {
                    const match = session.events.find((event) => event.sequence === sequence);
                    if (match) selectEvent(match);
                  }}
                />
              </section>
              <section className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
                <div>
                  <Kicker className="mb-3">Execution log</Kicker>
                  <EventLog events={session.events} selectedSequence={selectedEvent?.sequence} onSelect={selectEvent} />
                </div>
                <div>
                  <Kicker className="mb-3">Selected event</Kicker>
                  <SelectedEventInspector event={selectedEvent ?? session.last_event ?? null} />
                  <Kicker className="mb-3 mt-6">Approval workflows</Kicker>
                  <ul className="space-y-2 border border-border bg-inset/40 p-4 text-[13px] text-muted-foreground">
                    {sandbox.workflows.map((workflow) => (
                      <li key={workflow.name}>
                        <span className="text-foreground">{workflow.name}.</span> {workflow.description}
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
              <p className="text-[12px] text-muted-foreground">{session.limitation}</p>
            </div>
          ) : (
            <LockedNotice />
          )
        ) : null}
      </motion.div>
    </div>
  );
}

function SelectedEventInspector({ event }: { event: LabEvent | null }) {
  if (!event) {
    return (
      <div className="flex h-40 items-center justify-center border border-dashed border-border text-[13px] text-muted-foreground">
        Select a chart point, graph node, or log row.
      </div>
    );
  }
  return (
    <div className="border border-border bg-inset/50 p-4 font-mono text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <span className="text-foreground">#{event.sequence} · {event.tool}</span>
        <span className={event.allowed ? "text-success" : "text-destructive"}>{event.allowed ? "ALLOW" : "DENY"}</span>
      </div>
      <p className="mt-2 text-muted-foreground">{event.policy}</p>
      <pre className="mt-3 max-h-48 overflow-auto text-faint">{JSON.stringify({ arguments: event.arguments, output: event.output }, null, 2)}</pre>
    </div>
  );
}

function MetaStrip({ sandbox }: { sandbox: SandboxDetail }) {
  return (
    <div className="grid gap-3 border border-border bg-inset/40 p-4 font-mono text-[11px] sm:grid-cols-4">
      <Meta label="Tools" value={String(sandbox.tools.length)} />
      <Meta label="Scenarios" value={String(sandbox.scenarios.length)} />
      <Meta label="Datasets" value={String(sandbox.datasets.length)} />
      <Meta label="Status" value={sandbox.status} />
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-faint">{label}</p>
      <p className="mt-1 text-foreground tabular">{value}</p>
    </div>
  );
}

function LockedNotice() {
  return (
    <div className="border border-dashed border-border px-4 py-8 text-center text-[13px] text-muted-foreground">
      Enter the environment to load the live synthetic session. World, Instrument, and Trace bind to that session only.
    </div>
  );
}
