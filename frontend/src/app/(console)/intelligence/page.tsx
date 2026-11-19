import { Kicker, Panel, SectionHeader } from "@/components/layout";
import { ConsentForm } from "@/components/workspace-forms";
import { serverApi } from "@/lib/api";
import type { Consent, Session } from "@/lib/types";

type ConsentEvent = {
  id: string;
  granted: boolean;
  policy_version: string;
  permitted_categories: string[];
  intended_use: string;
  recorded_at: string;
};

type IntelligenceSummary = {
  approved_records: number;
  industry_categories: string[];
  attack_categories: string[];
  dataset_versions: { label: string; status: string }[];
  own_submissions: { pending_review: number; rejected: number; approved: number };
  benchmarks: { code: string; title: string; tests: number; method: string }[];
  disclaimer: string;
};

export default async function IntelligencePage() {
  const [session, consent, summary, history] = await Promise.all([
    serverApi<Session>("/auth/me"),
    serverApi<Consent>("/intelligence/consent"),
    serverApi<IntelligenceSummary>("/intelligence/summary"),
    serverApi<ConsentEvent[]>("/intelligence/consent-history"),
  ]);
  const canManage = session.role === "owner" || session.role === "admin";
  return (
    <div>
      <SectionHeader
        kicker="Dataset"
        title="Security intelligence"
        description="A permissioned dataset can be built later from validated assessment outcomes. Customer workspaces do not receive dataset records."
      />
      <Panel>
        <Kicker>Consent</Kicker>
        <h2 className="mt-1 text-[15px] font-medium">Contribution consent</h2>
        <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted-foreground">
          If you allow contribution, this organisation permits validated assessment outcomes to be considered for the intelligence dataset under policy {consent.policy_version}. The choice does not transfer data by itself, and it can be withdrawn. Consent is stored separately from assessment records.
        </p>
        <ConsentForm consent={consent} canManage={canManage} />
        <p className="mt-4 text-[13px] text-muted-foreground">
          Individual assessments stay in this organisation. A curated dataset only receives records after this opt-in and a separate review. Benchmarks describe the method. They are not a ranking of other customers.
        </p>
        {history.length > 0 ? (
          <ul className="mt-4 space-y-2 text-[13px]">
            {history.map((event) => (
              <li key={event.id} className="border-t border-border pt-2">
                {event.granted ? "Allowed" : "Not allowed"} · {event.policy_version} · {event.permitted_categories.join(", ") || "no categories"} · {event.intended_use}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-[13px] text-muted-foreground">No contribution decisions have been recorded.</p>
        )}
      </Panel>
      <Panel className="mt-4">
        <Kicker>Dataset</Kicker>
        <h2 className="mt-1 text-[15px] font-medium">Approved dataset</h2>
        {summary.approved_records === 0 ? (
          <p className="mt-2 text-[13px] leading-6 text-muted-foreground">No contributed records have been approved. Contribution is off until this organisation opts in, and approval is a separate review.</p>
        ) : (
          <p className="mt-2 text-[13px] text-muted-foreground">{summary.approved_records} approved records. Categories: {summary.attack_categories.join(", ") || "none"}. Industries: {summary.industry_categories.join(", ") || "none"}.</p>
        )}
        <p className="mt-3 text-[13px] text-muted-foreground">Your submissions — pending {summary.own_submissions.pending_review}, rejected {summary.own_submissions.rejected}, approved {summary.own_submissions.approved}.</p>
        <ul className="mt-4 space-y-3">
          {summary.benchmarks.map((benchmark) => (
            <li key={benchmark.code}>
              <p className="text-[13px] font-medium">{benchmark.title}</p>
              <p className="text-[13px] text-muted-foreground">{benchmark.method} Defined cases: {benchmark.tests}.</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[13px] text-muted-foreground">{summary.disclaimer}</p>
      </Panel>
      <Panel className="mt-4">
        <Kicker>Access</Kicker>
        <h2 className="mt-1 text-[15px] font-medium">Dataset access</h2>
        <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted-foreground">
          Intelligence records use a separate access check from organisation data. This account {session.user.is_platform_operator ? "is marked as a platform operator." : "is a customer account, so dataset contents are not shown here."}
        </p>
      </Panel>
    </div>
  );
}
