"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";
import { EChartsPanel } from "@/components/charts/echarts-panel";
import type { LabEvent } from "@/lib/types";

export function ActivityCharts({
  events,
  selectedSequence,
  onSelectSequence,
}: {
  events: LabEvent[];
  selectedSequence?: number | null;
  onSelectSequence?: (sequence: number) => void;
}) {
  const byTool = useMemo(() => {
    const map = new Map<string, { allowed: number; denied: number }>();
    for (const event of events) {
      const row = map.get(event.tool) ?? { allowed: 0, denied: 0 };
      if (event.allowed) row.allowed += 1;
      else row.denied += 1;
      map.set(event.tool, row);
    }
    return [...map.entries()].map(([tool, counts]) => ({ tool, ...counts }));
  }, [events]);

  const timeline = useMemo(
    () =>
      events.map((event) => ({
        sequence: event.sequence,
        value: event.allowed ? 1 : 0,
        tool: event.tool,
      })),
    [events],
  );

  const decisionsOption: EChartsOption = {
    title: { text: "Permission decisions by tool", left: 0, textStyle: { color: "#8b8f98", fontSize: 12, fontWeight: 400 } },
    legend: { data: ["Allowed", "Denied"], textStyle: { color: "#8b8f98" }, right: 0, top: 0 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: byTool.map((row) => row.tool),
      axisLabel: { color: "#8b8f98", rotate: byTool.length > 4 ? 28 : 0, fontSize: 10 },
      axisLine: { lineStyle: { color: "#23232b" } },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#8b8f98" },
      splitLine: { lineStyle: { color: "#23232b" } },
    },
    series: [
      { name: "Allowed", type: "bar", stack: "calls", data: byTool.map((row) => row.allowed), itemStyle: { color: "#3b82f6" }, barMaxWidth: 22 },
      { name: "Denied", type: "bar", stack: "calls", data: byTool.map((row) => row.denied), itemStyle: { color: "#e5534b" }, barMaxWidth: 22 },
    ],
  };

  const timelineOption: EChartsOption = {
    title: { text: "Execution sequence — click a point to select", left: 0, textStyle: { color: "#8b8f98", fontSize: 12, fontWeight: 400 } },
    tooltip: { trigger: "item" },
    xAxis: {
      type: "category",
      data: timeline.map((row) => `#${row.sequence}`),
      axisLabel: { color: "#8b8f98", fontSize: 10 },
      axisLine: { lineStyle: { color: "#23232b" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      interval: 1,
      axisLabel: {
        color: "#8b8f98",
        formatter: (value: number) => (value === 1 ? "allow" : value === 0 ? "deny" : ""),
      },
      splitLine: { lineStyle: { color: "#23232b" } },
    },
    series: [
      {
        type: "line",
        data: timeline.map((row) => row.value),
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { color: "#22d3ee", width: 1.5 },
        itemStyle: {
          color: (params: { dataIndex: number }) => {
            const row = timeline[params.dataIndex];
            if (row?.sequence === selectedSequence) return "#e8eaed";
            return row?.value ? "#3b82f6" : "#e5534b";
          },
        },
      },
    ],
  };

  if (events.length === 0) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        <EmptyChart label="Permission decisions appear after tool calls." />
        <EmptyChart label="Execution sequence appears after tool calls." />
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="border border-border bg-panel/40 p-3">
        <EChartsPanel
          option={decisionsOption}
          height={260}
          onEvents={{
            click: (params: { name?: string }) => {
              if (!params.name) return;
              const match = [...events].reverse().find((event) => event.tool === params.name);
              if (match) onSelectSequence?.(match.sequence);
            },
          }}
        />
      </div>
      <div className="border border-border bg-panel/40 p-3">
        <EChartsPanel
          option={timelineOption}
          height={260}
          onEvents={{
            click: (params: { dataIndex?: number }) => {
              const row = typeof params.dataIndex === "number" ? timeline[params.dataIndex] : null;
              if (row) onSelectSequence?.(row.sequence);
            },
          }}
        />
      </div>
    </div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="flex h-[260px] items-center justify-center border border-dashed border-border bg-inset/20 px-6 text-center text-[13px] text-muted-foreground">
      {label}
    </div>
  );
}
