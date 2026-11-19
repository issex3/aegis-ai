import { cn } from "@/lib/utils";
import { Kicker } from "@/components/layout/kicker";

export function SectionHeader({
  kicker,
  title,
  description,
  action,
  className,
}: {
  kicker?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-5 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {kicker ? <Kicker className="mb-2">{kicker}</Kicker> : null}
        <h1 className="font-display text-[28px] leading-[1.05] tracking-[-0.035em] text-foreground sm:text-[34px]">{title}</h1>
        {description ? <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
