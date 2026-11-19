import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  neutral: "border-border text-muted-foreground",
  active: "border-success/40 text-success",
  disabled: "border-border text-muted-foreground",
  draft: "border-border text-muted-foreground",
  high: "border-warning/40 text-warning",
  critical: "border-destructive/50 text-destructive",
  medium: "border-input text-foreground",
  low: "border-border text-muted-foreground",
  open: "border-warning/40 text-warning",
  info: "border-border text-muted-foreground",
};

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.08em]", tones[tone] ?? tones.neutral)}>
      {children}
    </span>
  );
}
