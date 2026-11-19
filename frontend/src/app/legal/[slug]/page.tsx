import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { cn } from "@/lib/utils";

const documents: Record<string, { title: string; body: string[] }> = {
  privacy: {
    title: "Privacy policy",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Aegis stores account details, organisation membership, agent configuration, assessment inputs that Aegis generates, observable agent responses, findings, and audit events.",
      "Customer assessment evidence stays in the customer organisation. It is not copied into a commercial dataset unless that organisation opts in and a reviewer approves a redacted record.",
      "API credentials are encrypted and are not shown again after they are stored.",
    ],
  },
  terms: {
    title: "Terms of service",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "An assessment is an automated check of a configured scope. It is not a penetration test, a compliance certification, or a promise that every weakness has been found.",
      "The internal score uses the published formula. It is not a security guarantee.",
    ],
  },
  "acceptable-use": {
    title: "Acceptable use policy",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Customers may test agents they are authorised to test. Aegis does not provide stealth, persistence, or unauthorised access tooling.",
      "Sandbox tools operate on fictional data. Real external side effects stay disabled unless a customer explicitly configures an authorised integration.",
    ],
  },
  contribution: {
    title: "Data contribution policy",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Accepting the product terms is not consent to contribute assessment data.",
      "Contribution is off until an owner records the categories and the intended use. Withdrawal stops future inclusion. It does not silently rewrite earlier decisions.",
      "Anonymisation is not treated as sufficient on its own for commercial use.",
    ],
  },
  licensing: {
    title: "Dataset licensing policy",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Only approved records with a recorded contribution basis can be exported or served through the licensed API.",
      "Exports omit customer names, credentials, and raw customer replies. A dataset is not described as fully anonymous.",
    ],
  },
  methodology: {
    title: "Assessment methodology",
    body: [
      "Tests send a defined input and record the observable reply and tool calls.",
      "PASS and FAIL results are scored. Errors, inconclusive results, and skipped tests are not treated as passes and are not penalised.",
      "Severity follows published rules. A failed test is not automatically critical.",
    ],
  },
  "responsible-testing": {
    title: "Responsible testing policy",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Every run requires an authorisation statement. Customers can cancel a running assessment.",
      "Aegis does not implement destructive testing or unauthorised access.",
    ],
  },
  retention: {
    title: "Data retention",
    body: [
      "This is a draft for review by a qualified solicitor before publication.",
      "Assessment records, findings, reports, and audit events are kept for the life of the organisation account unless a later retention schedule is agreed.",
      "Withdrawn contribution consent excludes future dataset submissions. Approved records already in a dataset version remain subject to the licence terms recorded at approval.",
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(documents).map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  return { title: documents[slug]?.title ?? "Document" };
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const document = documents[slug];
  if (!document) {
    notFound();
  }
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto grid max-w-[1240px] gap-10 px-4 py-12 sm:gap-12 sm:px-5 sm:py-16 md:px-8 lg:grid-cols-[14rem_1fr] lg:py-24">
        <nav aria-label="Documents" className="lg:sticky lg:top-28 lg:self-start">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">Documents</p>
          <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 lg:flex-col lg:gap-y-2">
            {Object.entries(documents).map(([key, item]) => (
              <li key={key}>
                <Link
                  href={`/legal/${key}`}
                  aria-current={key === slug ? "page" : undefined}
                  className={cn("inline-flex min-h-10 items-center text-[13px] lg:min-h-0", key === slug ? "text-foreground" : "text-muted-foreground transition-colors hover:text-foreground")}
                >
                  {item.title}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <article className="max-w-2xl">
          <p className="inline-block border border-signal/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-signal">
            Draft · solicitor review required
          </p>
          <h1 className="mt-6 text-[clamp(2rem,4vw,3rem)] font-medium leading-[1.05] tracking-[-0.03em]">{document.title}</h1>
          <div className="mt-10 space-y-5 border-t border-border pt-8 text-[15px] leading-7 text-muted-foreground">
            {document.body.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
        </article>
      </main>
      <SiteFooter />
    </div>
  );
}
