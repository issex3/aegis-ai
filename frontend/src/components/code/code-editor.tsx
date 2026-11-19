"use client";

import CodeMirror, { type ReactCodeMirrorProps } from "@uiw/react-codemirror";
import { EditorView } from "@codemirror/view";
import { cn } from "@/lib/utils";

const aegisEditorTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "var(--editor-bg)",
      color: "var(--foreground)",
      fontSize: "13px",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
    },
    ".cm-scroller": {
      fontFamily: "var(--font-geist-mono), ui-monospace, monospace",
      lineHeight: "1.5",
    },
    ".cm-content": {
      caretColor: "var(--signal)",
      padding: "12px 0",
    },
    ".cm-gutters": {
      backgroundColor: "var(--editor-gutter)",
      color: "var(--faint)",
      borderRight: "1px solid var(--border)",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "var(--secondary)",
    },
    ".cm-activeLine": {
      backgroundColor: "rgba(23, 23, 26, 0.85)",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "rgba(227, 162, 67, 0.22)",
    },
    ".cm-cursor": {
      borderLeftColor: "var(--signal)",
    },
  },
  { dark: true },
);

type CodeEditorProps = Omit<ReactCodeMirrorProps, "theme"> & {
  className?: string;
};

/**
 * Read/write code surface for prompts, tool payloads, and evidence inspection.
 * Add language packages (e.g. @codemirror/lang-json) at call sites when needed.
 */
export function CodeEditor({ className, extensions = [], basicSetup, ...props }: CodeEditorProps) {
  return (
    <div className={cn("min-w-0 overflow-hidden", className)}>
      <CodeMirror
        theme="none"
        extensions={[aegisEditorTheme, ...extensions]}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: true,
          highlightSelectionMatches: false,
          ...((typeof basicSetup === "object" ? basicSetup : {}) as object),
        }}
        {...props}
      />
    </div>
  );
}
