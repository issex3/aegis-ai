import { cn } from "@/lib/utils";

export function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div className="w-full overflow-x-auto overscroll-x-contain [-webkit-overflow-scrolling:touch]">
      <table className={cn("w-full caption-bottom text-[13px]", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      className={cn(
        "border-b border-border text-left font-mono text-[10px] uppercase tracking-[0.12em] text-faint",
        className,
      )}
      {...props}
    />
  );
}

export function TableBody(props: React.ComponentProps<"tbody">) {
  return <tbody {...props} />;
}

export function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      className={cn(
        "border-b border-border last:border-0 transition-colors hover:bg-secondary/40 data-[state=selected]:bg-secondary/70",
        className,
      )}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return <th className={cn("h-8 px-3 font-medium", className)} {...props} />;
}

export function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return <td className={cn("px-3 py-2.5 align-middle", className)} {...props} />;
}
