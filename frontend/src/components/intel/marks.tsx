import { cn } from "@/lib/utils";
import { outcomeFill, outcomeTone, riskTone } from "@/lib/labels";

const riskSquares: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, informational: 0 };

export function RiskMark({ risk, className }: { risk: string; className?: string }) {
  const filled = riskSquares[risk] ?? 0;
  return (
    <span className={cn("inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.06em]", riskTone[risk] ?? "text-muted-foreground", className)}>
      <span className="inline-flex gap-[2px]" aria-hidden="true">
        {[0, 1, 2, 3].map((index) => (
          <span key={index} className={cn("h-2.5 w-[3px]", index < filled ? "bg-current" : "bg-border")} />
        ))}
      </span>
      {risk}
    </span>
  );
}

export function OutcomeLabel({ outcome }: { outcome: string }) {
  return <span className={cn("font-mono text-[11px] tracking-[0.06em]", outcomeTone[outcome] ?? "text-muted-foreground")}>{outcome}</span>;
}

export function PriorityLabel({ priority }: { priority: string | null }) {
  if (!priority) return <span className="font-mono text-[11px] text-faint">n/a</span>;
  return (
    <span
      className={cn(
        "inline-flex h-5 min-w-7 items-center justify-center border px-1 font-mono text-[10px]",
        priority === "P1" ? "border-signal/60 text-signal" : priority === "P2" ? "border-input text-foreground" : "border-border text-muted-foreground",
      )}
    >
      {priority}
    </span>
  );
}

export function OutcomeBar({ counts, className }: { counts: Record<string, number>; className?: string }) {
  const order = ["FAIL", "INCONCLUSIVE", "ERROR", "SKIPPED", "PASS"];
  const total = order.reduce((sum, key) => sum + (counts[key] ?? 0), 0);
  if (total === 0) return <div className={cn("h-1.5 w-full bg-border", className)} />;
  return (
    <div className={cn("flex h-1.5 w-full gap-px overflow-hidden", className)} role="img" aria-label={order.map((key) => `${counts[key] ?? 0} ${key.toLowerCase()}`).join(", ")}>
      {order.map((key) =>
        counts[key] ? <span key={key} className={outcomeFill[key]} style={{ width: `${((counts[key] ?? 0) / total) * 100}%` }} /> : null,
      )}
    </div>
  );
}

export function Kicker({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn("font-mono text-[10px] uppercase tracking-[0.16em] text-faint", className)}>{children}</p>;
}

export function Stat({ label, value, note, tone }: { label: string; value: React.ReactNode; note?: string; tone?: string }) {
  return (
    <div className="min-w-0">
      <Kicker>{label}</Kicker>
      <p className={cn("mt-2 font-display text-4xl leading-none tabular", tone)}>{value}</p>
      {note ? <p className="mt-2 text-[12px] leading-5 text-muted-foreground">{note}</p> : null}
    </div>
  );
}
