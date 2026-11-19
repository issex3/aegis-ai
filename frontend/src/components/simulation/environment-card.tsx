import Link from "next/link";
import { LAB_IDENTITY, resolveLabKey } from "@/lib/simulation";
import type { SandboxCatalogueItem } from "@/lib/types";
import { titleCase } from "@/lib/labels";
import { cn } from "@/lib/utils";

/** Differentiated catalogue row — not a twin card. */
export function EnvironmentIndexRow({
  item,
  compact = false,
}: {
  item: SandboxCatalogueItem;
  compact?: boolean;
}) {
  const key = resolveLabKey(item);
  const identity = key ? LAB_IDENTITY[key] : null;

  return (
    <div
      className={cn(
        "grid gap-3 border-b border-border px-4 py-4 last:border-0 md:grid-cols-[1.2fr_0.7fr_0.5fr_0.5fr_0.5fr_auto] md:items-center",
        compact && "bg-inset/30",
      )}
    >
      <div className="min-w-0">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
          {identity?.label ?? item.industry_name}
          {compact ? " · featured" : ""}
        </p>
        <p className="mt-1 truncate text-[14px] font-medium text-foreground">{item.name}</p>
        <p className="mt-1 line-clamp-2 text-[12px] leading-5 text-muted-foreground md:hidden">
          {identity?.blurb ?? item.description}
        </p>
        <p className="mt-1 hidden text-[12px] leading-5 text-muted-foreground md:line-clamp-1">
          {(item.datasets ?? []).slice(0, 4).join(" · ") || identity?.blurb}
        </p>
      </div>
      <div className="text-[12px] text-muted-foreground">
        <span className="md:hidden font-mono text-[10px] uppercase text-faint">Roles · </span>
        {(item.roles ?? []).slice(0, 3).map((r) => titleCase(r)).join(", ") || "—"}
        {(item.roles?.length ?? 0) > 3 ? ` +${(item.roles?.length ?? 0) - 3}` : ""}
      </div>
      <div className="tabular text-[13px]">
        <span className="md:hidden font-mono text-[10px] uppercase text-faint">Tools · </span>
        {item.tools.length}
      </div>
      <div className="tabular text-[13px]">
        <span className="md:hidden font-mono text-[10px] uppercase text-faint">Scenarios · </span>
        {item.scenario_count}
      </div>
      <div className="tabular text-[13px]">
        <span className="md:hidden font-mono text-[10px] uppercase text-faint">Classes · </span>
        {item.data_classes?.length ?? 0}
      </div>
      <div>
        <Link
          href={`/sandboxes/${item.id}`}
          className="inline-flex h-8 items-center border border-border px-3 text-[12px] text-foreground transition-colors hover:border-signal hover:text-signal"
        >
          Enter
        </Link>
      </div>
    </div>
  );
}

/** @deprecated Prefer EnvironmentIndexRow — kept for any residual imports. */
export function EnvironmentCard({ item }: { item: SandboxCatalogueItem }) {
  return (
    <div className="border border-border">
      <EnvironmentIndexRow item={item} />
    </div>
  );
}
