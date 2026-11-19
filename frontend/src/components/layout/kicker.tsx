import { cn } from "@/lib/utils";

export function Kicker({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("text-kicker", className)} {...props} />;
}
