"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { cn } from "@/lib/utils";

type Run = {
  label: string;
  when: string;
  outcome: "PASS" | "FAIL";
  status: string;
  observed: string;
};

const runs: Run[] = [
  {
    label: "Baseline",
    when: "Before change",
    outcome: "PASS",
    status: "Clean",
    observed: "Agent stays in scope. No tool calls, nothing leaked.",
  },
  {
    label: "Rerun",
    when: "After a quiet change",
    outcome: "FAIL",
    status: "New finding",
    observed: "A canary string shows up in the reply.",
  },
  {
    label: "Retest",
    when: "After the fix",
    outcome: "PASS",
    status: "Closed",
    observed: "Boundary holds. Finding closed.",
  },
];

export function RegressionStory() {
  const [selected, setSelected] = useState(1);
  const reduce = useReducedMotion();
  const run = runs[selected];

  return (
    <div className="border border-border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 font-mono text-[11px]">
        <div className="flex min-w-0 items-center gap-3 text-muted-foreground">
          <span className="shrink-0 text-foreground">accounting.control</span>
          <span className="hidden text-faint sm:inline" aria-hidden="true">
            /
          </span>
          <span className="hidden truncate sm:inline">Does the agent keep invoices in its own queue?</span>
        </div>
        <span className="border border-signal/40 px-1.5 py-0.5 uppercase tracking-[0.12em] text-signal">Simulated</span>
      </div>

      <p className="border-b border-border px-4 py-3 text-[14px] leading-6 text-muted-foreground sm:hidden">
        Does the agent keep invoices in its own queue?
      </p>

      <div className="grid lg:grid-cols-[1.2fr_1fr]">
        <div className="border-b border-border lg:border-b-0 lg:border-r">
          <div className="grid grid-cols-[minmax(0,1fr)_5.5rem_4rem] gap-3 border-b border-border px-4 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
            <span>Run</span>
            <span>Compared to</span>
            <span className="text-right">Outcome</span>
          </div>
          <ul role="listbox" aria-label="Regression runs">
            {runs.map((item, i) => (
              <li key={item.label}>
                <button
                  type="button"
                  role="option"
                  aria-selected={i === selected}
                  onClick={() => setSelected(i)}
                  className={cn(
                    "relative grid min-h-12 w-full grid-cols-[minmax(0,1fr)_5.5rem_4rem] items-center gap-3 border-b border-border/60 px-4 py-3 text-left transition-colors last:border-b-0",
                    i === selected ? "bg-secondary" : "hover:bg-secondary/50",
                  )}
                >
                  {i === selected ? <span className="absolute inset-y-0 left-0 w-px bg-foreground" aria-hidden="true" /> : null}
                  <span className="min-w-0">
                    <span className="block font-mono text-[12px] text-foreground">{item.label}</span>
                    <span className="block truncate text-[12px] text-muted-foreground">{item.when}</span>
                  </span>
                  <span className="font-mono text-[11px] text-faint">{item.status}</span>
                  <span className={cn("text-right font-mono text-[11px]", item.outcome === "PASS" ? "text-success" : "text-foreground")}>
                    {item.outcome}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={run.label}
            initial={reduce ? false : { opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduce ? undefined : { opacity: 0, x: -8 }}
            transition={{ duration: 0.22 }}
            className="flex flex-col justify-between px-5 py-5"
          >
            <div className="space-y-5">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">Observed</p>
                <p className={cn("mt-2 text-[15px] leading-6", run.outcome === "FAIL" ? "text-foreground" : "text-muted-foreground")}>
                  {run.observed}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-px border border-border bg-border font-mono text-[11px]">
                <div className="bg-card px-3 py-2.5">
                  <dt className="text-faint">Run</dt>
                  <dd className="mt-0.5 text-foreground">{run.label}</dd>
                </div>
                <div className="bg-card px-3 py-2.5">
                  <dt className="text-faint">Outcome</dt>
                  <dd className={cn("mt-0.5", run.outcome === "PASS" ? "text-success" : "text-foreground")}>{run.outcome}</dd>
                </div>
              </dl>
            </div>
            <p className="mt-8 font-mono text-[11px] leading-5 text-faint">
              Same test ID across runs. Aegis marks what changed.
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
