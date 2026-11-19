"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

type TraceEvent = {
  tool: string;
  target: string;
  decision: "allowed" | "denied";
  policy: string;
};

const tools = [
  "search_invoice",
  "approve_payment",
  "view_payroll",
  "retrieve_customer_record",
  "create_payment_request",
  "update_supplier_details",
];

const events: TraceEvent[] = [
  { tool: "search_invoice", target: "INV-100", decision: "allowed", policy: "accounting.search_invoice" },
  { tool: "approve_payment", target: "PR-9", decision: "denied", policy: "accounting.payment_approval" },
  { tool: "view_payroll", target: "EMP-1", decision: "denied", policy: "accounting.payroll_restricted" },
  { tool: "retrieve_customer_record", target: "CLI-2", decision: "denied", policy: "client_scope" },
  { tool: "create_payment_request", target: "INV-100", decision: "allowed", policy: "accounting.payment_draft" },
  { tool: "update_supplier_details", target: "SUP-1", decision: "denied", policy: "accounting.supplier_update" },
];

const CX = 300;
const CY = 250;
const R = 164;

const round = (value: number) => Math.round(value * 100) / 100;

function point(index: number, radius = R) {
  const angle = (index / tools.length) * Math.PI * 2 - Math.PI / 2;
  return { x: round(CX + Math.cos(angle) * radius), y: round(CY + Math.sin(angle) * radius) };
}

const ticks = Array.from({ length: 96 }, (_, i) => {
  const angle = (i / 96) * Math.PI * 2;
  const inner = i % 8 === 0 ? 224 : 230;
  return {
    x1: round(CX + Math.cos(angle) * inner),
    y1: round(CY + Math.sin(angle) * inner),
    x2: round(CX + Math.cos(angle) * 236),
    y2: round(CY + Math.sin(angle) * 236),
    major: i % 8 === 0,
  };
});

const SIGNAL = "#e3a243";

export function HeroVisual() {
  const reduce = useReducedMotion();
  const [step, setStep] = useState(3);

  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(() => setStep((value) => value + 1), 1900);
    return () => window.clearInterval(id);
  }, [reduce]);

  const active = events[step % events.length];
  const activeIndex = tools.indexOf(active.tool);
  const target = point(activeIndex, R - 14);
  const log = Array.from({ length: 4 }, (_, i) => {
    const n = step - i;
    return { n, event: events[((n % events.length) + events.length) % events.length] };
  }).filter((entry) => entry.n >= 0);

  return (
    <figure className="relative" aria-label="Illustrative trace of an agent calling tools in the synthetic accounting sandbox">
      <svg viewBox="-60 6 720 488" className="h-auto w-full" role="img" aria-hidden="true">
        <defs>
          <pattern id="hv-grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M20 0H0V20" fill="none" stroke="#ededea" strokeOpacity="0.035" />
          </pattern>
          <radialGradient id="hv-fade">
            <stop offset="55%" stopColor="#fff" />
            <stop offset="100%" stopColor="#000" />
          </radialGradient>
          <mask id="hv-mask">
            <rect x="-60" width="720" height="500" fill="url(#hv-fade)" />
          </mask>
        </defs>
        <rect x="-60" width="720" height="500" fill="url(#hv-grid)" mask="url(#hv-mask)" />

        {ticks.map(({ major, ...coords }, i) => (
          <line key={i} {...coords} stroke="#ededea" strokeOpacity={major ? 0.35 : 0.12} strokeWidth="1" />
        ))}
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="#ededea" strokeOpacity="0.1" />
        <circle cx={CX} cy={CY} r={96} fill="none" stroke="#ededea" strokeOpacity="0.08" strokeDasharray="2 5" />
        <path d={`M${CX - 250} ${CY}H${CX - 240}M${CX + 240} ${CY}H${CX + 250}`} stroke="#ededea" strokeOpacity="0.3" />

        {tools.map((tool, i) => {
          const p = point(i, R - 14);
          return <line key={tool} x1={CX} y1={CY} x2={p.x} y2={p.y} stroke="#ededea" strokeOpacity="0.06" />;
        })}

        <motion.line
          key={`probe-${step}`}
          x1={CX}
          y1={CY}
          x2={target.x}
          y2={target.y}
          stroke={active.decision === "denied" ? SIGNAL : "#ededea"}
          strokeWidth="1.25"
          initial={reduce ? false : { pathLength: 0, opacity: 1 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        />

        {tools.map((tool, i) => {
          const p = point(i);
          const isActive = i === activeIndex;
          const denied = isActive && active.decision === "denied";
          const left = p.x < CX - 10;
          const right = p.x > CX + 10;
          const anchor = left ? "end" : right ? "start" : "middle";
          const dx = left ? -14 : right ? 14 : 0;
          const dy = !left && !right ? (p.y < CY ? -16 : 24) : 4;
          return (
            <g key={tool}>
              <rect
                x={p.x - 5}
                y={p.y - 5}
                width="10"
                height="10"
                fill={isActive ? (denied ? SIGNAL : "#ededea") : "#09090a"}
                stroke={isActive ? (denied ? SIGNAL : "#ededea") : "#5c5c58"}
                style={{ transition: "fill 300ms, stroke 300ms" }}
              />
              <text
                x={p.x + dx}
                y={p.y + dy}
                textAnchor={anchor}
                fontFamily="var(--font-geist-mono)"
                fontSize="13"
                fill={isActive ? "#ededea" : "#7a7a75"}
                style={{ transition: "fill 300ms" }}
              >
                {tool}
              </text>
            </g>
          );
        })}

        <rect x={CX - 88} y={CY - 28} width="176" height="56" fill="#09090a" stroke="#ededea" strokeOpacity="0.5" />
        <text x={CX} y={CY - 4} textAnchor="middle" fontFamily="var(--font-geist-mono)" fontSize="11" fill="#8b8b85" letterSpacing="1.5">
          AGENT UNDER TEST
        </text>
        <text x={CX} y={CY + 13} textAnchor="middle" fontFamily="var(--font-geist-mono)" fontSize="12" fill="#ededea">
          role: accounts_clerk
        </text>
      </svg>

      <div className="mt-2 h-[6.75rem] overflow-hidden border-t border-border pt-3 font-mono text-[11px] leading-6" aria-live="off">
        <AnimatePresence initial={false}>
          {log.map(({ n, event }, i) => (
            <motion.div
              key={n}
              layout={!reduce}
              initial={reduce ? false : { opacity: 0, y: -6 }}
              animate={{ opacity: i === 0 ? 1 : 0.55 - i * 0.12, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="grid grid-cols-[2.75rem_minmax(0,1fr)_auto] gap-2 sm:grid-cols-[3.5rem_1fr_auto] sm:gap-3 sm:whitespace-nowrap"
            >
              <span className="text-faint">{String(n + 1).padStart(4, "0")}</span>
              <span className="truncate text-muted-foreground">
                <span className="text-foreground">{event.tool}</span>({event.target}) <span className="hidden sm:inline">· {event.policy}</span>
              </span>
              <span className={event.decision === "denied" ? "text-signal" : "text-success"}>{event.decision.toUpperCase()}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </figure>
  );
}
