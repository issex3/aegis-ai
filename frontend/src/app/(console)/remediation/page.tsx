import { Kicker, Panel, SectionHeader } from "@/components/layout";
import { serverApi } from "@/lib/api";

type Guide = {
  category: string;
  title: string;
  explanation: string;
  why: string;
  controls: string[];
  verification: string;
  tests: string[];
};

export default async function RemediationPage() {
  const guides = await serverApi<Guide[]>("/remediation");
  return (
    <div>
      <SectionHeader
        kicker="Controls"
        title="Remediation"
        description="General controls tied to the test cases in this release. These are not patches for a particular agent framework."
      />
      <div className="grid gap-4">
        {guides.map((guide) => (
          <Panel key={guide.category}>
            <Kicker>{guide.category}</Kicker>
            <h2 className="mt-1 text-[15px] font-medium">{guide.title}</h2>
            <p className="mt-2 text-[13px] leading-6 text-muted-foreground">{guide.explanation}</p>
            <p className="mt-2 text-[13px] leading-6">{guide.why}</p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-[13px] text-muted-foreground">
              {guide.controls.map((control) => (
                <li key={control}>{control}</li>
              ))}
            </ul>
            <p className="mt-3 text-[13px]">{guide.verification}</p>
            <p className="mt-2 font-mono text-[11px] text-muted-foreground">{guide.tests.join(" · ")}</p>
          </Panel>
        ))}
      </div>
    </div>
  );
}
