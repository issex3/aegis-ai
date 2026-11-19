"use client";

import { json } from "@codemirror/lang-json";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CodeEditor } from "@/components/code/code-editor";
import type { LabEvent, LabTool } from "@/lib/types";
import { titleCase } from "@/lib/labels";

function seedArgs(tool: LabTool | undefined) {
  if (!tool) return "{\n}";
  const seed: Record<string, string> = {};
  for (const key of Object.keys(tool.params)) seed[key] = "";
  return JSON.stringify(seed, null, 2);
}

export function ToolConsole({
  tools,
  role,
  busy,
  lastEvent,
  onInvoke,
  onInspectEvent,
}: {
  tools: LabTool[];
  role: string;
  busy?: boolean;
  lastEvent?: LabEvent | null;
  onInvoke: (tool: string, argumentsJson: string) => Promise<void>;
  onInspectEvent?: (event: LabEvent) => void;
}) {
  const [toolName, setToolName] = useState(tools[0]?.name ?? "");
  const [argsByTool, setArgsByTool] = useState<Record<string, string>>({});
  const selected = useMemo(() => tools.find((tool) => tool.name === toolName) ?? tools[0], [tools, toolName]);
  const argsText = selected ? (argsByTool[selected.name] ?? seedArgs(selected)) : "{}";
  const jsonExt = useMemo(() => [json()], []);

  const paramHint = useMemo(() => {
    if (!selected) return null;
    const keys = Object.keys(selected.params ?? {});
    if (!keys.length) return "No declared parameters for this tool.";
    return `Schema hints · ${keys.map((key) => `${key}: ${String(selected.params[key] ?? "any")}`).join(" · ")}`;
  }, [selected]);

  const inspection = useMemo(() => {
    if (!lastEvent) return '{\n  "note": "Invoke a tool to inspect arguments and output."\n}';
    return JSON.stringify(
      {
        tool: lastEvent.tool,
        allowed: lastEvent.allowed,
        policy: lastEvent.policy,
        arguments: lastEvent.arguments,
        output: lastEvent.output,
      },
      null,
      2,
    );
  }, [lastEvent]);

  async function submit() {
    if (!selected) return;
    try {
      JSON.parse(argsText);
    } catch {
      toast.error("Arguments must be valid JSON.");
      return;
    }
    await onInvoke(selected.name, argsText);
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="space-y-3 border border-border bg-panel/40 p-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">Tool invoke</p>
            <p className="mt-1 text-[13px] text-muted-foreground">Calls the live sandbox handler for role {titleCase(role)}.</p>
          </div>
          <Button type="button" size="sm" disabled={busy || !selected} onClick={submit}>
            Execute
          </Button>
        </div>
        <label className="block text-[12px] text-muted-foreground">
          Tool
          <select
            className="mt-1 h-9 w-full border border-input bg-inset px-3 text-[13px] text-foreground"
            value={selected?.name ?? ""}
            onChange={(event) => setToolName(event.target.value)}
          >
            {tools.map((tool) => {
              const permitted = tool.roles.includes(role);
              return (
                <option key={tool.name} value={tool.name}>
                  {tool.name}
                  {permitted ? "" : " (denied for role)"}
                </option>
              );
            })}
          </select>
        </label>
        {selected ? (
          <p className="text-[12px] leading-5 text-muted-foreground">
            {selected.description} · roles {selected.roles.map(titleCase).join(", ")}
          </p>
        ) : null}
        {paramHint ? <p className="font-mono text-[10px] text-faint">{paramHint}</p> : null}
        <CodeEditor
          value={argsText}
          height="220px"
          extensions={jsonExt}
          onChange={(value) => {
            if (!selected) return;
            setArgsByTool((prev) => ({ ...prev, [selected.name]: value }));
          }}
        />
      </div>
      <div className="space-y-3 border border-border bg-panel/40 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">Last observation</p>
          {lastEvent ? (
            <button
              type="button"
              className="text-[11px] text-signal hover:underline"
              onClick={() => onInspectEvent?.(lastEvent)}
            >
              Open in Trace
            </button>
          ) : null}
        </div>
        <CodeEditor value={inspection} height="320px" editable={false} extensions={jsonExt} basicSetup={{ lineNumbers: true, foldGutter: true }} />
      </div>
    </div>
  );
}
