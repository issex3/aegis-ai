"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { clientApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const profiles = [
  { value: "default", note: "Planted weaknesses" },
  { value: "regressed", note: "Also fails the control case" },
  { value: "remediated", note: "Declines and calls no tools" },
] as const;

export function DemoProfileControl({ agentId, current }: { agentId: string; current: string }) {
  const router = useRouter();
  const [value, setValue] = useState(current);
  const [pending, setPending] = useState(false);

  async function choose(profile: string) {
    if (profile === value || pending) return;
    setPending(true);
    const result = await clientApi(`/agents/${agentId}/demo-profile`, { method: "POST", body: JSON.stringify({ profile }) });
    setPending(false);
    if (!result.ok) {
      toast.error(result.error.error.message);
      return;
    }
    setValue(profile);
    toast.success(`Demo profile set to ${profile}. Results remain simulated.`);
    router.refresh();
  }

  return (
    <fieldset disabled={pending}>
      <legend className="text-sm font-semibold">Demo behaviour profile</legend>
      <p className="mt-1 text-[12px] leading-5 text-muted-foreground">Applies to the next assessment run.</p>
      <div className="mt-3 border border-border" role="radiogroup" aria-label="Demo behaviour profile">
        {profiles.map((profile) => (
          <button
            key={profile.value}
            type="button"
            role="radio"
            aria-checked={value === profile.value}
            onClick={() => choose(profile.value)}
            className={cn(
              "flex w-full items-baseline justify-between gap-3 border-b border-border px-3 py-2 text-left last:border-b-0 transition-colors",
              value === profile.value ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60",
            )}
          >
            <span className="font-mono text-[12px]">{profile.value}</span>
            <span className="text-[11px] text-faint">{profile.note}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
