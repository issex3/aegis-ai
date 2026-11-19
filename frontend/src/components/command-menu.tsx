"use client";

import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const destinations = [
  { href: "/dashboard", label: "Overview", group: "Investigate" },
  { href: "/sandboxes", label: "Simulation Lab", group: "Investigate" },
  { href: "/agents", label: "Agents", group: "Test" },
  { href: "/programmes", label: "Programmes", group: "Test" },
  { href: "/library", label: "Scenario library", group: "Test" },
  { href: "/assessments", label: "Assessments", group: "Test" },
  { href: "/findings", label: "Findings", group: "Evidence" },
  { href: "/reports", label: "Reports", group: "Evidence" },
  { href: "/remediation", label: "Remediation", group: "Evidence" },
  { href: "/intelligence", label: "Intelligence", group: "Organisation" },
  { href: "/settings", label: "Settings", group: "Organisation" },
];

const groups = ["Investigate", "Test", "Evidence", "Organisation"];

export function CommandMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    function onOpen() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("aegis-command", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("aegis-command", onOpen);
    };
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 sm:items-start sm:px-4 sm:pt-[15vh]" onClick={() => setOpen(false)}>
      <Command
        className="w-full max-w-xl overflow-hidden border-t border-input bg-overlay text-foreground sm:border"
        onClick={(event) => event.stopPropagation()}
        label="Search console"
      >
        <Command.Input
          autoFocus
          placeholder="Jump to a console page"
          className="w-full border-b border-border bg-transparent px-4 py-4 text-base outline-none placeholder:text-muted-foreground sm:py-3 sm:text-sm"
        />
        <Command.List className="max-h-[min(24rem,70dvh)] overflow-auto p-2">
          <Command.Empty className="px-3 py-6 text-sm text-muted-foreground">No matching page.</Command.Empty>
          {groups.map((group) => (
            <Command.Group key={group} heading={group} className="px-2 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
              {destinations
                .filter((item) => item.group === group)
                .map((item) => (
                  <Command.Item
                    key={item.href}
                    value={item.label}
                    onSelect={() => {
                      setOpen(false);
                      router.push(item.href);
                    }}
                    className="min-h-11 cursor-pointer border-l border-transparent px-2 py-3 font-sans text-sm normal-case tracking-normal text-muted-foreground data-[selected=true]:border-signal data-[selected=true]:bg-secondary data-[selected=true]:text-foreground sm:min-h-0 sm:py-2"
                  >
                    {item.label}
                  </Command.Item>
                ))}
            </Command.Group>
          ))}
        </Command.List>
        <div className="border-t border-border px-4 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Ctrl K · console only</div>
      </Command>
    </div>
  );
}

export function openCommandMenu() {
  window.dispatchEvent(new Event("aegis-command"));
}
