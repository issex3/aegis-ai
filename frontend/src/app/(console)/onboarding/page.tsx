import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { serverApi } from "@/lib/api";

type Step = { id: string; label: string; done: boolean };

const links: Record<string, string> = {
  agent: "/agents",
  integration: "/agents/new",
  connection: "/agents",
  industry: "/sandboxes",
  assessment: "/assessments",
  results: "/findings",
};

export default async function OnboardingPage() {
  const state = await serverApi<{ steps: Step[]; complete: boolean }>("/onboarding");
  return (
    <div>
      <PageHeader
        kicker="Start"
        title="Onboarding"
        description="These steps follow the records already stored for this organisation. A demo agent counts as a connection because it does not use an external credential. Industry environments live in Simulation Lab."
      />
      <ol className="space-y-3">
        {state.steps.map((step, index) => (
          <li key={step.id}>
            <Card className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{step.done ? "Done" : "Open"}</p>
                <p className="mt-1 text-sm font-medium">
                  {index + 1}. {step.label}
                </p>
              </div>
              {links[step.id] ? (
                <Link href={links[step.id]} className="text-sm underline underline-offset-4">
                  Open
                </Link>
              ) : null}
            </Card>
          </li>
        ))}
      </ol>
    </div>
  );
}
