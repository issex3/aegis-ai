"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type ReactFlowProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

type FlowCanvasProps = ReactFlowProps & {
  className?: string;
  showMiniMap?: boolean;
  showControls?: boolean;
};

function FlowCanvasInner({
  className,
  showMiniMap = false,
  showControls = true,
  children,
  proOptions,
  ...props
}: FlowCanvasProps) {
  const reduce = useReducedMotion();

  return (
    <div className={cn("aegis-flow h-full min-h-[280px] w-full", className)}>
      <ReactFlow
        fitView
        minZoom={0.35}
        maxZoom={1.75}
        nodesDraggable={!reduce}
        nodesConnectable={!reduce}
        elementsSelectable
        panOnScroll
        zoomOnDoubleClick={!reduce}
        proOptions={{ hideAttribution: true, ...proOptions }}
        defaultEdgeOptions={{
          style: { stroke: "var(--flow-edge)", strokeWidth: 1.25 },
          ...props.defaultEdgeOptions,
        }}
        {...props}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--flow-dot)" />
        {showControls ? <Controls showInteractive={!reduce} /> : null}
        {showMiniMap ? (
          <MiniMap
            pannable
            zoomable
            maskColor="rgba(9, 9, 10, 0.55)"
            nodeColor="#17171a"
            nodeStrokeColor="#2c2c30"
          />
        ) : null}
        {children}
      </ReactFlow>
    </div>
  );
}

/**
 * Themed React Flow surface for simulation graphs and tool/call graphs.
 * Wrap usages that need `useReactFlow` with this provider-backed canvas.
 */
export function FlowCanvas(props: FlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
