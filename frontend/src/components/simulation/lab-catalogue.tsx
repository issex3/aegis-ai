"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NumberTicker } from "@/components/motion/number-ticker";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { Kicker } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { LAB_IDENTITY, resolveLabKey, sortLabCatalogue } from "@/lib/simulation";
import type { SandboxCatalogueItem } from "@/lib/types";
import { titleCase } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { aegisEase } from "@/lib/motion-presets";

type Planned = { name: string; status: string; description: string };

export function LabCatalogue({
  available,
  planned,
}: {
  available: SandboxCatalogueItem[];
  planned: Planned[];
}) {
  const environments = useMemo(() => sortLabCatalogue(available), [available]);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(true);
  const reduce = useReducedMotion();
  const active = environments[index] ?? null;
  const key = active ? resolveLabKey(active) : null;
  const identity = key ? LAB_IDENTITY[key] : null;

  useEffect(() => {
    if (reduce || paused || environments.length < 2) return;
    const id = window.setInterval(() => {
      setIndex((value) => (value + 1) % environments.length);
    }, 5200);
    return () => window.clearInterval(id);
  }, [environments.length, paused, reduce]);

  const toolTotal = environments.reduce((n, row) => n + row.tools.length, 0);
  const scenarioTotal = environments.reduce((n, row) => n + row.scenario_count, 0);

  return (
    <div>
      <Reveal>
        <div className="mb-6 flex flex-col gap-3 sm:mb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Kicker>Investigate</Kicker>
            <h1 className="mt-2 font-display text-[32px] leading-[1.02] tracking-[-0.04em] sm:text-[40px]">Simulation Lab</h1>
            <p className="mt-2 max-w-xl text-[13px] leading-6 text-muted-foreground">
              Enter synthetic industry environments for controlled AI security research. Live catalogue counts only.
            </p>
          </div>
        </div>
      </Reveal>

      <Stagger className="mb-6 grid gap-2.5 sm:grid-cols-3">
        {[
          { label: "Environments", value: environments.length },
          { label: "Tools exposed", value: toolTotal },
          { label: "Library scenarios", value: scenarioTotal },
        ].map((stat) => (
          <StaggerItem key={stat.label}>
            <div className="surface rounded-md px-4 py-3">
              <Kicker>{stat.label}</Kicker>
              <p className="mt-2 text-metric">
                <NumberTicker value={stat.value} />
              </p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>

      {active ? (
        <Reveal delay={0.08}>
          <section
            className="relative mb-8 overflow-hidden rounded-lg border border-border bg-panel"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background: `radial-gradient(820px 320px at 12% -10%, color-mix(in oklab, ${identity?.accentVar ?? "var(--signal)"} 32%, transparent), transparent 58%)`,
              }}
            />
            <div className="relative grid gap-0 lg:grid-cols-[1.35fr_0.9fr]">
              <div className="border-b border-border bg-panel/40 p-5 sm:p-6 lg:border-b-0 lg:border-r">
                <div className="flex items-center justify-between gap-3">
                  <Kicker>Featured environment</Kicker>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      aria-label="Previous environment"
                      className="grid h-8 w-8 place-items-center rounded-md border border-border bg-inset/60 text-muted-foreground hover:text-foreground"
                      onClick={() => setIndex((value) => (value - 1 + environments.length) % environments.length)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      aria-label="Next environment"
                      className="grid h-8 w-8 place-items-center rounded-md border border-border bg-inset/60 text-muted-foreground hover:text-foreground"
                      onClick={() => setIndex((value) => (value + 1) % environments.length)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div key={active.id}>
                  <h2 className="mt-4 font-display text-[36px] leading-none tracking-[-0.04em] text-foreground sm:text-[44px]">
                    {identity?.label ?? active.industry_name}
                  </h2>
                  <p className="mt-2 text-[14px] text-muted-foreground">{active.name}</p>
                  <p className="mt-3 max-w-xl text-[13px] leading-6 text-muted-foreground">{active.description}</p>
                  <p className="mt-2 max-w-xl text-[12px] text-faint">{identity?.blurb}</p>
                  <div className="mt-6 flex flex-wrap gap-2">
                    <Button asChild>
                      <Link href={`/sandboxes/${active.id}`}>Enter environment</Link>
                    </Button>
                    <Button variant="outline" asChild>
                      <Link href="/library">Browse scenarios</Link>
                    </Button>
                  </div>
                </div>

                <div className="mt-7 flex flex-wrap gap-1.5">
                  {environments.map((item, i) => (
                    <button
                      key={item.id}
                      type="button"
                      aria-label={`Show ${item.name}`}
                      onClick={() => setIndex(i)}
                      className={cn(
                        "h-1.5 rounded-full transition-all",
                        i === index ? "w-7 bg-signal" : "w-1.5 bg-white/15 hover:bg-white/30",
                      )}
                    />
                  ))}
                </div>
              </div>

              <div key={`stats-${active.id}`} className="grid grid-cols-2 gap-px bg-border">
                {[
                  { label: "Roles", value: active.roles?.length ?? 0 },
                  { label: "Tools", value: active.tools.length },
                  { label: "Scenarios", value: active.scenario_count },
                  { label: "Data classes", value: active.data_classes?.length ?? 0 },
                ].map((cell) => (
                  <div key={cell.label} className="bg-panel/95 px-4 py-5">
                    <Kicker>{cell.label}</Kicker>
                    <p className="mt-2 text-metric">
                      <NumberTicker value={cell.value} />
                    </p>
                  </div>
                ))}
                <div className="col-span-2 bg-panel/95 px-4 py-4">
                  <Kicker>Surfaces</Kicker>
                  <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
                    {(active.datasets ?? []).slice(0, 6).join(" · ") || "—"}
                  </p>
                  <p className="mt-2 text-[11px] text-faint">
                    {active.categories.map((c) => titleCase(c)).join(" · ") || "—"}
                  </p>
                </div>
              </div>
            </div>
          </section>
        </Reveal>
      ) : null}

      <Reveal delay={0.12}>
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <Kicker>Catalogue</Kicker>
            <h2 className="mt-1 text-[17px] font-medium tracking-tight">Environment index</h2>
          </div>
        </div>
        <div className="overflow-hidden rounded-md border border-border surface">
          <div className="hidden grid-cols-[1.3fr_0.7fr_0.45fr_0.45fr_0.45fr_auto] gap-3 border-b border-border bg-inset/50 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-faint md:grid">
            <span>Environment</span>
            <span>Roles</span>
            <span>Tools</span>
            <span>Scenarios</span>
            <span>Classes</span>
            <span />
          </div>
          {environments.map((item, i) => {
            const rowKey = resolveLabKey(item);
            const rowIdentity = rowKey ? LAB_IDENTITY[rowKey] : null;
            return (
              <motion.div
                key={item.id}
                initial={reduce ? false : { opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.35, delay: Math.min(i * 0.04, 0.24), ease: aegisEase }}
                className="grid gap-3 border-b border-border px-4 py-3.5 last:border-0 md:grid-cols-[1.3fr_0.7fr_0.45fr_0.45fr_0.45fr_auto] md:items-center hover:bg-white/[0.025]"
              >
                <div className="min-w-0">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{rowIdentity?.label ?? item.industry_name}</p>
                  <p className="mt-1 truncate text-[13px] font-medium">{item.name}</p>
                  <p className="mt-1 hidden text-[12px] text-muted-foreground md:line-clamp-1">
                    {(item.datasets ?? []).slice(0, 4).join(" · ") || rowIdentity?.blurb}
                  </p>
                </div>
                <div className="text-[12px] text-muted-foreground">
                  {(item.roles ?? []).slice(0, 3).map((r) => titleCase(r)).join(", ") || "—"}
                </div>
                <div className="tabular text-[13px]">{item.tools.length}</div>
                <div className="tabular text-[13px]">{item.scenario_count}</div>
                <div className="tabular text-[13px]">{item.data_classes?.length ?? 0}</div>
                <div>
                  <Link
                    href={`/sandboxes/${item.id}`}
                    className="inline-flex h-7 items-center rounded-md border border-border px-2.5 text-[12px] transition-colors hover:border-signal hover:text-signal"
                  >
                    Enter
                  </Link>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Reveal>

      {planned.length ? (
        <Reveal delay={0.16}>
          <section className="mt-8 border-t border-border pt-6">
            <Kicker>Planned</Kicker>
            <p className="mt-2 max-w-2xl text-[13px] text-muted-foreground">
              Catalogue growth — not enterable until a sandbox definition ships.
            </p>
            <ul className="mt-4 grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
              {planned.map((industry) => (
                <li key={industry.name} className="rounded-md border border-dashed border-border bg-inset/40 px-4 py-3">
                  <p className="font-mono text-[10px] uppercase tracking-wide text-faint">Not available</p>
                  <p className="mt-1 text-[13px] font-medium">{industry.name}</p>
                  <p className="mt-1 text-[12px] text-muted-foreground">{industry.description}</p>
                </li>
              ))}
            </ul>
          </section>
        </Reveal>
      ) : null}
    </div>
  );
}
