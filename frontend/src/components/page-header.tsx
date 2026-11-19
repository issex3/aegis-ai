import { SectionHeader } from "@/components/layout/section-header";

/** Thin adapter over SectionHeader for gradual migration. */
export function PageHeader({
  kicker,
  title,
  description,
  action,
}: {
  kicker?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return <SectionHeader kicker={kicker} title={title} description={description} action={action} />;
}
