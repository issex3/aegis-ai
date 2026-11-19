"use client";

import { VirtualList } from "@/components/data/virtual-list";
import type { LabEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

export function EventLog({
  events,
  selectedSequence,
  onSelect,
}: {
  events: LabEvent[];
  selectedSequence?: number | null;
  onSelect?: (event: LabEvent) => void;
}) {
  const rows = [...events].reverse();

  if (rows.length === 0) {
    return (
      <div className="flex h-[360px] items-center justify-center border border-dashed border-border text-sm text-muted-foreground">
        No execution events in this session yet.
      </div>
    );
  }

  return (
    <VirtualList
      items={rows}
      estimateSize={64}
      height={360}
      className="border border-border bg-card/30"
      getItemKey={(item) => item.sequence}
      renderItem={(event) => (
        <button
          type="button"
          onClick={() => onSelect?.(event)}
          className={cn(
            "flex h-full w-full items-start gap-3 border-b border-border px-3 py-2 text-left transition-colors hover:bg-secondary/50",
            selectedSequence === event.sequence && "bg-secondary",
          )}
        >
          <span className="font-mono text-[10px] text-faint">#{event.sequence}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-mono text-[12px] text-foreground">{event.tool}</span>
            <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">{event.policy}</span>
          </span>
          <span className={cn("font-mono text-[10px] uppercase", event.allowed ? "text-success" : "text-destructive")}>
            {event.allowed ? "allow" : "deny"}
          </span>
        </button>
      )}
    />
  );
}
