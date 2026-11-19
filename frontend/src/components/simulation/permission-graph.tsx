"use client";

import { useCallback, useMemo } from "react";
import {
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { FlowCanvas } from "@/components/flow/flow-canvas";
import type { LabGraph } from "@/lib/types";
import { cn } from "@/lib/utils";

function LabNode({ data }: NodeProps) {
  const kind = String(data.kind ?? "system");
  const allowed = data.allowed;
  return (
    <div
      className={cn(
        "min-w-[128px] border bg-card px-3 py-2 text-[11px]",
        kind === "agent" && "border-signal",
        kind === "role" && "border-cyan/60",
        kind === "tool" && (allowed ? "border-success/50" : "border-destructive/40"),
        kind === "system" && "border-border",
      )}
    >
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-faint" />
      <p className="font-mono text-[9px] uppercase tracking-wide text-faint">{kind}</p>
      <p className="mt-1 font-medium text-foreground">{String(data.label)}</p>
      {kind === "tool" ? (
        <p className={cn("mt-1 font-mono text-[9px]", allowed ? "text-success" : "text-destructive")}>
          {allowed ? "permitted" : "denied"}
        </p>
      ) : null}
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-faint" />
    </div>
  );
}

const nodeTypes = { lab: LabNode };

export function PermissionGraph({
  graph,
  highlightTool,
  onSelectTool,
}: {
  graph: LabGraph;
  highlightTool?: string | null;
  onSelectTool?: (tool: string) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const tools = graph.nodes.filter((n) => n.type === "tool");
    const systems = graph.nodes.filter((n) => n.type === "system");
    const mapped: Node[] = [
      {
        id: "agent",
        type: "lab",
        position: { x: 24, y: 120 },
        data: { ...graph.nodes.find((n) => n.id === "agent")?.data, label: "Simulated agent", kind: "agent" },
      },
      {
        id: "role",
        type: "lab",
        position: { x: 220, y: 120 },
        data: { ...graph.nodes.find((n) => n.id === "role")?.data, label: graph.nodes.find((n) => n.id === "role")?.label, kind: "role" },
      },
      ...tools.map((node, index) => ({
        id: node.id,
        type: "lab" as const,
        position: { x: 440, y: 24 + index * 72 },
        data: { ...node.data, label: node.label, kind: "tool" },
        style: highlightTool && node.label === highlightTool ? { boxShadow: "0 0 0 1px var(--signal)" } : undefined,
      })),
      ...systems.map((node, index) => ({
        id: node.id,
        type: "lab" as const,
        position: { x: 700, y: 40 + index * 64 },
        data: { ...node.data, label: node.label, kind: "system" },
      })),
    ];

    const mappedEdges: Edge[] = graph.edges.map((edge) => {
      const allowed = edge.data?.allowed !== false && edge.label !== "deny";
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        animated: Boolean(highlightTool && edge.target === `tool:${highlightTool}`),
        style: {
          stroke: allowed ? "var(--signal)" : "var(--destructive)",
          strokeWidth: 1.1,
          opacity: allowed ? 0.85 : 0.45,
        },
        markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: allowed ? "var(--signal)" : "var(--destructive)" },
      };
    });

    return { nodes: mapped, edges: mappedEdges };
  }, [graph, highlightTool]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const kind = node.data?.kind;
      const label = node.data?.label;
      if (kind === "tool" && typeof label === "string") {
        onSelectTool?.(label);
      }
    },
    [onSelectTool],
  );

  return (
    <FlowCanvas
      className="h-[420px] border border-border"
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      nodesDraggable={false}
      showControls
      showMiniMap={false}
      proOptions={{ hideAttribution: true }}
      onNodeClick={onNodeClick}
    />
  );
}
