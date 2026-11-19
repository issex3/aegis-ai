import { cn } from "@/lib/utils";

export function Toolbar({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 border-b border-border bg-panel/40 px-3 py-2",
        className,
      )}
      {...props}
    />
  );
}
