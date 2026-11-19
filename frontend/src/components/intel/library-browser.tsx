"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Kicker, RiskMark } from "@/components/intel/marks";
import { riskOrder, scenarioCategoryLabels } from "@/lib/labels";
import type { LibraryIndex } from "@/lib/types";
import { cn } from "@/lib/utils";

const selectClass = "h-11 w-full border border-border bg-background px-2 text-base text-foreground outline-none focus:border-input sm:h-8 sm:w-auto sm:text-[13px]";

export function LibraryBrowser({ index }: { index: LibraryIndex }) {
  const [industry, setIndustry] = useState<string>("all");
  const [risk, setRisk] = useState<string>("all");
  const [threat, setThreat] = useState<string>("all");
  const [category, setCategory] = useState<string>("all");
  const [query, setQuery] = useState("");

  const threatNames = useMemo(() => Object.fromEntries(index.threats.map((item) => [item.key, item.name])), [index.threats]);
  const scoped = index.scenarios.filter((item) => industry === "all" || item.industry === industry);
  const visible = scoped.filter((item) => {
    if (risk !== "all" && item.risk !== risk) return false;
    if (threat !== "all" && item.threat !== threat) return false;
    if (category !== "all" && item.category !== category) return false;
    if (query) {
      const haystack = `${item.code} ${item.name} ${item.description} ${item.technique}`.toLowerCase();
      if (!haystack.includes(query.toLowerCase())) return false;
    }
    return true;
  });
  const threatCoverage = index.threats
    .map((item) => ({ ...item, count: scoped.filter((scenario) => scenario.threat === item.key).length }))
    .filter((item) => item.count > 0);
  const maxCount = Math.max(1, ...threatCoverage.map((item) => item.count));
  const active = index.industries.find((item) => item.slug === industry);

  return (
    <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <nav aria-label="Industries" className="lg:sticky lg:top-20 lg:self-start">
        <Kicker>Industries</Kicker>
        <ul className="mt-3 border-t border-border">
          {[{ slug: "all", name: "All industries", scenarios: index.scenarios.length, by_risk: null as null | Record<string, number> }, ...index.industries].map((item) => (
            <li key={item.slug}>
              <button
                type="button"
                onClick={() => setIndustry(item.slug)}
                aria-pressed={industry === item.slug}
                className={cn(
                  "relative w-full border-b border-border py-3 pl-3 pr-2 text-left transition-colors",
                  industry === item.slug ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground",
                )}
              >
                {industry === item.slug ? <span className="absolute inset-y-0 left-0 w-px bg-signal" aria-hidden="true" /> : null}
                <span className="flex items-baseline justify-between gap-2 text-[13px]">
                  {item.name}
                  <span className="font-mono text-[11px] text-faint tabular">{item.scenarios}</span>
                </span>
                {item.by_risk ? (
                  <span className="mt-2 flex h-1 gap-px" aria-hidden="true">
                    {riskOrder.map((level) =>
                      item.by_risk?.[level] ? (
                        <span
                          key={level}
                          className={cn(level === "critical" ? "bg-destructive" : level === "high" ? "bg-signal" : level === "medium" ? "bg-muted-foreground" : "bg-faint")}
                          style={{ flexGrow: item.by_risk[level] }}
                        />
                      ) : null,
                    )}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[12px] leading-5 text-faint">Each industry runs in its own synthetic sandbox. Add industries by registering a sandbox and a library module.</p>
      </nav>

      <div className="min-w-0">
        <div className="grid gap-6 border border-border bg-card p-5 md:grid-cols-[1fr_1.2fr]">
          <div>
            <Kicker>{active ? active.sandbox_name : "Library"}</Kicker>
            <h2 className="mt-2 text-xl font-medium tracking-[-0.015em]">{active ? active.name : "Every industry scenario"}</h2>
            <p className="mt-2 text-[13px] leading-6 text-muted-foreground">
              {active ? active.summary : `${index.scenarios.length} versioned scenarios across ${index.industries.length} industries. Each one runs a simulated workflow and checks actions, not just text.`}
            </p>
          </div>
          <div>
            <Kicker>Threat coverage</Kicker>
            <ul className="mt-3 space-y-1.5">
              {threatCoverage.map((item) => (
                <li key={item.key}>
                  <button type="button" onClick={() => setThreat(threat === item.key ? "all" : item.key)} aria-pressed={threat === item.key} className="group grid min-h-10 w-full grid-cols-[3.25rem_minmax(0,1fr)_1.25rem] items-center gap-2 text-left sm:grid-cols-[3.25rem_minmax(0,1fr)_4rem_1.25rem] sm:gap-3">
                    <span className={cn("font-mono text-[11px]", threat === item.key ? "text-signal" : "text-faint group-hover:text-muted-foreground")}>{item.key}</span>
                    <span className={cn("truncate text-[12px]", threat === item.key ? "text-foreground" : "text-muted-foreground")}>{item.name}</span>
                    <span className="hidden h-1 bg-border sm:block">
                      <span className={cn("block h-full", threat === item.key ? "bg-signal" : "bg-muted-foreground")} style={{ width: `${(item.count / maxCount) * 100}%` }} />
                    </span>
                    <span className="text-right font-mono text-[11px] text-muted-foreground tabular">{item.count}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search scenarios"
            aria-label="Search scenarios"
            className="h-11 w-full border border-border bg-background px-3 text-base outline-none placeholder:text-faint focus:border-input sm:h-8 sm:w-56 sm:px-2 sm:text-[13px]"
          />
          <div className="flex overflow-x-auto border border-border" role="group" aria-label="Risk level">
            {["all", ...riskOrder].map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => setRisk(level)}
                aria-pressed={risk === level}
                className={cn("h-11 shrink-0 px-3 font-mono text-[11px] uppercase tracking-[0.06em] transition-colors sm:h-8 sm:px-2.5", risk === level ? "bg-secondary text-foreground" : "text-faint hover:text-muted-foreground")}
              >
                {level}
              </button>
            ))}
          </div>
          <select aria-label="Threat class" value={threat} onChange={(event) => setThreat(event.target.value)} className={selectClass}>
            <option value="all">All threat classes</option>
            {index.threats.map((item) => (
              <option key={item.key} value={item.key}>
                {item.key} · {item.name}
              </option>
            ))}
          </select>
          <select aria-label="Category" value={category} onChange={(event) => setCategory(event.target.value)} className={selectClass}>
            <option value="all">All categories</option>
            {index.categories.map((item) => (
              <option key={item} value={item}>
                {scenarioCategoryLabels[item] ?? item}
              </option>
            ))}
          </select>
          <span className="ml-auto font-mono text-[11px] text-faint">
            {visible.length} of {scoped.length}
          </span>
        </div>

        <div className="mt-3 border border-border">
          <div className="hidden grid-cols-[minmax(0,1fr)_6.5rem_7rem] gap-4 border-b border-border px-4 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint md:grid">
            <span>Scenario</span>
            <span>Threat</span>
            <span>Risk</span>
          </div>
          {visible.length === 0 ? (
            <p className="px-4 py-10 text-center text-[13px] text-muted-foreground">No scenario matches these filters.</p>
          ) : (
            <ul>
              {visible.map((item) => (
                <li key={item.code} className="border-b border-border/70 last:border-b-0">
                  <Link href={`/library/${item.code}`} className="grid gap-2 px-4 py-3.5 transition-colors hover:bg-secondary/60 md:grid-cols-[minmax(0,1fr)_6.5rem_7rem] md:items-center md:gap-4">
                    <span className="min-w-0">
                      <span className="flex items-baseline gap-3">
                        <span className="truncate text-[14px] text-foreground">{item.name}</span>
                        {item.variants ? <span className="shrink-0 font-mono text-[10px] text-faint">+{item.variants} variant</span> : null}
                      </span>
                      <span className="mt-1 block truncate font-mono text-[11px] text-faint">
                        {item.code} · v{item.version} · {item.technique}
                      </span>
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground" title={threatNames[item.threat]}>
                      {item.threat}
                    </span>
                    <RiskMark risk={item.risk} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
