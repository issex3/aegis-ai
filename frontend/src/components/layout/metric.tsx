import { cn } from "@/lib/utils";
import { Kicker } from "@/components/layout/kicker";

export function Metric({
  label,
  value,
  hint,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={cn("surface rounded-md px-4 py-3.5", className)}>
      <Kicker>{label}</Kicker>
      <div className="mt-2.5 text-metric text-foreground">{value}</div>
      {hint ? <p className="mt-1.5 text-meta">{hint}</p> : null}
    </div>
  );
}
