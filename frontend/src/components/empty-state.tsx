import { Panel } from "@/components/layout/panel";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <Panel className="relative overflow-hidden px-6 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(500px_180px_at_0%_0%,rgba(91,141,239,0.12),transparent)]" />
      <div className="relative">
        <h2 className="text-base font-medium tracking-tight">{title}</h2>
        <p className="mt-2 max-w-xl text-[13px] leading-6 text-muted-foreground">{body}</p>
        {action ? <div className="mt-5">{action}</div> : null}
      </div>
    </Panel>
  );
}
