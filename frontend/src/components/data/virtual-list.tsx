"use client";

import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { cn } from "@/lib/utils";

type VirtualListProps<T> = {
  items: T[];
  estimateSize?: number;
  overscan?: number;
  className?: string;
  height?: number | string;
  getItemKey?: (item: T, index: number) => string | number;
  renderItem: (item: T, index: number) => React.ReactNode;
};

/**
 * Windowed list for long evidence / log / finding feeds without mounting every row.
 */
export function VirtualList<T>({
  items,
  estimateSize = 44,
  overscan = 8,
  className,
  height = 360,
  getItemKey,
  renderItem,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  // TanStack Virtual intentionally returns unstable function identities; React Compiler skips this boundary.
  // eslint-disable-next-line react-hooks/incompatible-library -- useVirtualizer is the supported virtualization API
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
    getItemKey: getItemKey ? (index) => getItemKey(items[index]!, index) : undefined,
  });

  return (
    <div
      ref={parentRef}
      className={cn("overflow-auto overscroll-contain", className)}
      style={{ height }}
      role="list"
    >
      <div className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const item = items[virtualRow.index]!;
          return (
            <div
              key={virtualRow.key}
              role="listitem"
              className="absolute left-0 top-0 w-full"
              style={{
                height: virtualRow.size,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {renderItem(item, virtualRow.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
