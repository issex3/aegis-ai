"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";
import { useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import { aegisChartBase } from "@/lib/chart-theme";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-secondary/40" aria-hidden />,
});

type EChartsPanelProps = {
  option: EChartsOption;
  className?: string;
  height?: number | string;
  /** When false, skips Aegis chrome merge (caller owns full option). */
  themed?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvents?: Record<string, (params: any) => void>;
};

/**
 * Lazy ECharts host. Pass real series data only — never fabricate security events.
 * Existing Recharts `CountChart` remains for simple bars already in production.
 */
export function EChartsPanel({ option, className, height = 240, themed = true, onEvents }: EChartsPanelProps) {
  const reduce = useReducedMotion();
  const base = themed ? aegisChartBase(option) : option;
  const merged: EChartsOption = {
    ...base,
    animation: reduce ? false : base.animation !== false,
  };

  return (
    <div className={cn("w-full min-w-0 overflow-hidden", className)} style={{ height }}>
      <ReactECharts
        option={merged}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
        notMerge
        lazyUpdate
        onEvents={onEvents}
      />
    </div>
  );
}
