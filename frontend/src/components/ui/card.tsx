import { cn } from "@/lib/utils";

/** Prefer Panel for non-interactive surfaces. Card is for interactive containers. */
export function Card({ className, ...props }: React.ComponentProps<"section">) {
  return <section className={cn("border border-border bg-panel/80", className)} {...props} />;
}
