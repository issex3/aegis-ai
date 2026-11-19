import type { EChartsOption } from "echarts";

/** Aegis ECharts chrome — terminal-grade, no neon / glass defaults. */
export const aegisChartColors = {
  background: "transparent",
  text: "#8b8b85",
  axis: "#8b8b85",
  split: "#222225",
  series: ["#3b82f6", "#22d3ee", "#e8eaed", "#3d9a6a", "#e5534b"],
  tooltipBg: "#121218",
  tooltipBorder: "#2a2a34",
  tooltipText: "#e8eaed",
} as const;

export function aegisChartBase(option: EChartsOption = {}): EChartsOption {
  const tooltipExtras =
    typeof option.tooltip === "object" && option.tooltip && !Array.isArray(option.tooltip)
      ? option.tooltip
      : {};
  const gridExtras =
    typeof option.grid === "object" && option.grid && !Array.isArray(option.grid) ? option.grid : {};

  return {
    ...option,
    color: option.color ?? [...aegisChartColors.series],
    backgroundColor: option.backgroundColor ?? aegisChartColors.background,
    textStyle: {
      color: aegisChartColors.text,
      fontFamily: "var(--font-geist), system-ui, sans-serif",
      ...(typeof option.textStyle === "object" && option.textStyle ? option.textStyle : {}),
    },
    tooltip: {
      backgroundColor: aegisChartColors.tooltipBg,
      borderColor: aegisChartColors.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: aegisChartColors.tooltipText, fontSize: 12 },
      ...tooltipExtras,
    },
    grid: {
      left: 40,
      right: 16,
      top: 24,
      bottom: 32,
      containLabel: true,
      ...gridExtras,
    },
  };
}
