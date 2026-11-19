"use client";

import { useState } from "react";

export function TagInput({
  id,
  values,
  onChange,
  placeholder,
}: {
  id: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  function commit() {
    const value = draft.trim();
    if (value && !values.includes(value) && values.length < 25) onChange([...values, value.slice(0, 200)]);
    setDraft("");
  }

  return (
    <div className="flex min-h-9 flex-wrap items-center gap-1.5 border border-input bg-background px-2 py-1.5 focus-within:border-muted-foreground">
      {values.map((value) => (
        <span key={value} className="inline-flex items-center gap-1.5 border border-border bg-secondary px-2 py-0.5 text-[12px]">
          {value}
          <button type="button" onClick={() => onChange(values.filter((item) => item !== value))} className="text-faint hover:text-foreground" aria-label={`Remove ${value}`}>
            ×
          </button>
        </span>
      ))}
      <input
        id={id}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            commit();
          } else if (event.key === "Backspace" && !draft && values.length) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={commit}
        placeholder={values.length ? "" : placeholder}
        className="min-w-[10rem] flex-1 bg-transparent py-0.5 text-[13px] outline-none placeholder:text-faint"
      />
    </div>
  );
}
