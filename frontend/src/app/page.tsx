import Link from "next/link";
import { HeroVisual } from "@/components/site/hero-visual";
import { ProductPreview } from "@/components/site/product-preview";
import { RegressionStory } from "@/components/site/regression-story";
import { Reveal } from "@/components/site/reveal";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";

const specs = [
  { value: "38", label: "Industry scenarios", note: "" },
  { value: "30", label: "Catalogue test cases", note: "" },
  { value: "44", label: "Simulated tools", note: "" },
  { value: "10", label: "Threat classes", note: "OWASP LLM 2025 and Aegis classes" },
];

const method = [
  {
    title: "Connect the agent you operate",
    body: "Point Aegis at an OpenAI-compatible endpoint, or use the built-in demonstration agent. Credentials are encrypted at rest, masked in the interface, and never returned to the browser.",
    meta: "Outbound requests pass an SSRF guard",
  },
  {
    title: "Profile it, and the scenarios follow",
    body: "Describe the agent's industry, responsibilities, tools, and permissions. Aegis selects the industry scenarios that apply, explains every exclusion, and ranks the rest by risk. You review the programme before anything runs.",
    meta: "Customer service · Accounting · Healthcare · Legal · Sales and CRM",
  },
  {
    title: "Run simulated workflows, not single prompts",
    body: "Each scenario gives the agent a role and real-shaped tools over fictional records. Tool results go back to the agent, and Aegis checks what it requested, what the sandbox allowed, and what changed. It never claims to see hidden reasoning.",
    meta: "Timeouts are errors. Missing tool support is inconclusive.",
  },
  {
    title: "Classify with rules you can read",
    body: "A failure is not automatically critical. Severity follows a published rule: observed evidence, the boundary crossed, and confidence. Weak evidence lowers severity rather than inflating it.",
    meta: "critical 10 · high 7 · medium 4 · low 1",
  },
  {
    title: "Baseline, rerun, compare",
    body: "Mark a run as the baseline. Later runs are compared by test identifier, so a fix shows as resolved and a new weakness shows as new. Export the record as a PDF.",
    meta: "Scheduled reruns run on the worker queue",
  },
];

const sandboxes = [
  {
    name: "Customer support desk",
    role: "support_agent",
    coverage: "10 scenarios",
    records: "Customers, orders, refund policy, internal playbook, uploaded attachments",
    tools: ["lookup_customer", "search_order", "issue_refund", "update_account_details", "read_attachment", "escalate_to_human", "get_policy"],
  },
  {
    name: "Accounting operations",
    role: "accounts_clerk",
    coverage: "10 scenarios · 7 catalogue cases",
    records: "Invoices, payroll, supplier bank details, finance inbox, ledger and journal",
    tools: ["search_invoice", "retrieve_customer_record", "view_payroll", "create_payment_request", "approve_payment", "update_supplier_details", "read_inbox_message", "update_invoice", "generate_management_report", "post_journal_entry"],
  },
  {
    name: "Outpatient clinic services",
    role: "patient_services",
    coverage: "6 scenarios",
    records: "Patients, appointments, restricted clinical notes, access grants, triage protocol",
    tools: ["lookup_patient", "view_appointments", "view_clinical_notes", "send_patient_message", "update_record_access", "get_triage_protocol"],
  },
  {
    name: "Legal matter workspace",
    role: "legal_assistant",
    coverage: "6 scenarios · 6 catalogue cases",
    records: "Two clients' matters, privileged drafts, an executed lease",
    tools: ["search_case", "retrieve_document", "view_client_record", "create_case_note", "share_document", "change_document_permissions", "edit_document"],
  },
  {
    name: "Sales CRM workspace",
    role: "sales_rep",
    coverage: "6 scenarios",
    records: "Owned and foreign accounts, contacts, deals, discount limits, inbox, simulated outbox",
    tools: ["search_contacts", "view_account", "export_contacts", "update_contact", "apply_discount", "update_deal_stage", "send_email", "read_inbox_message"],
  },
  {
    name: "Retail support desk",
    role: "support_agent",
    coverage: "7 catalogue cases",
    records: "Orders, customer profiles, refunds, inventory, deliveries",
    tools: ["search_order", "retrieve_customer", "issue_refund_request", "modify_order", "view_inventory", "update_delivery_information"],
  },
];

const planned = ["Insurance", "Recruitment", "Property", "Education", "Financial services beyond accounting", "Logistics"];

const refusals = [
  "It does not certify compliance or describe an agent as secure.",
  "It is not a penetration test, and Aegis itself has not been independently penetration tested.",
  "A sandbox result is evidence about behaviour under test, not proof about a live system.",
  "It runs no destructive, stealth, or persistence techniques against real systems.",
  "Customer results feed shared intelligence only with explicit, revocable consent.",
  "There are no customer logos, counts, or testimonials here, because none are being claimed.",
];

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">{children}</p>;
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main>
        <section className="relative overflow-hidden">
          <div className="mx-auto grid max-w-[1240px] gap-10 px-4 pb-16 pt-10 sm:px-5 sm:pb-20 sm:pt-14 md:px-8 lg:grid-cols-[1fr_1.05fr] lg:gap-10 lg:pb-28 lg:pt-20">
            <div className="flex min-w-0 flex-col justify-center">
              <Reveal>
                <h1 className="text-[clamp(2.05rem,8.4vw,4.6rem)] font-medium leading-[1.05] tracking-[-0.035em] sm:leading-[1.02]">
                  Your agent can approve payments.{" "}
                  <span className="font-display italic tracking-[-0.01em] text-muted-foreground sm:whitespace-nowrap">Should it?</span>
                </h1>
              </Reveal>
              <Reveal delay={0.1}>
                <p className="mt-6 max-w-[34rem] text-[16px] leading-7 text-muted-foreground sm:mt-7 sm:text-[17px]">
                  Find out which barriers your agent will cross
                </p>
              </Reveal>
              <Reveal delay={0.15}>
                <div className="mt-8 flex flex-col gap-4 sm:mt-10 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-7">
                  <Link href="/register" className="group inline-flex min-h-12 items-center justify-center gap-3 bg-foreground px-5 py-3 text-sm font-medium text-background transition-opacity hover:opacity-90 sm:min-h-0">
                    Start an assessment
                    <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">→</span>
                  </Link>
                  <Link href="/demo" className="inline-flex min-h-11 items-center text-sm text-foreground underline decoration-input underline-offset-[6px] transition-colors hover:decoration-foreground sm:min-h-0">
                    Walk through the demonstration
                  </Link>
                </div>
              </Reveal>
            </div>
            <Reveal delay={0.1} className="lg:pl-6">
              <HeroVisual />
            </Reveal>
          </div>
        </section>

        <section aria-label="Catalogue" className="border-y border-border">
          <div className="mx-auto grid max-w-[1240px] grid-cols-2 md:grid-cols-4">
            {specs.map((spec, i) => (
              <div key={spec.label} className={`px-4 py-7 sm:px-5 sm:py-8 md:px-8 ${i % 2 === 1 ? "border-l" : ""} ${i >= 2 ? "border-t md:border-t-0" : ""} ${i === 2 ? "md:border-l" : ""} border-border`}>
                <p className="font-display text-4xl leading-none tabular sm:text-5xl">{spec.value}</p>
                <p className="mt-4 text-[13px] text-foreground">{spec.label}</p>
                {spec.note ? <p className="mt-1 text-[12px] text-faint">{spec.note}</p> : null}
              </div>
            ))}
          </div>
        </section>

        <section id="product" className="scroll-mt-20">
          <div className="mx-auto max-w-[1240px] px-4 py-16 sm:px-5 sm:py-24 md:px-8 lg:py-32">
            <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr] lg:items-end">
              <Reveal>
                <Eyebrow>The assessment record</Eyebrow>
                <h2 className="mt-5 text-[2rem] font-medium leading-[1.08] tracking-[-0.03em] sm:text-4xl md:text-5xl">
                  Every finding carries <span className="font-display italic text-muted-foreground">its own evidence.</span>
                </h2>
              </Reveal>
              <Reveal delay={0.05}>
                <p className="max-w-xl text-[15px] leading-7 text-muted-foreground lg:ml-auto">
                  The probe, the expected behaviour, what the agent actually returned, the tool call it requested, and the rule that set the severity. Select a row. These are the demonstration agent&apos;s results in the accounting sandbox, which runs the 10 generic cases alongside the 7 accounting ones.
                </p>
              </Reveal>
            </div>
            <Reveal delay={0.1} className="mt-14">
              <ProductPreview />
            </Reveal>
          </div>
        </section>

        <section id="method" className="scroll-mt-20 border-t border-border">
          <div className="mx-auto grid max-w-[1240px] gap-10 px-4 py-16 sm:gap-14 sm:px-5 sm:py-24 md:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-32">
            <div className="lg:sticky lg:top-28 lg:self-start">
              <Eyebrow>Method</Eyebrow>
              <h2 className="mt-5 text-[2rem] font-medium leading-[1.08] tracking-[-0.03em] sm:text-4xl md:text-5xl">
                Controlled, <span className="font-display italic text-muted-foreground">repeatable,</span> and on the record.
              </h2>
              <Link href="/legal/methodology" className="mt-6 inline-block text-sm underline decoration-input underline-offset-[6px] hover:decoration-foreground">
                Read the methodology
              </Link>
            </div>
            <ol className="border-t border-border">
              {method.map((step, i) => (
                <li key={step.title}>
                  <Reveal className="grid gap-4 border-b border-border py-9 md:grid-cols-[4rem_1fr]">
                    <span className="font-mono text-[12px] text-signal">{String(i + 1).padStart(2, "0")}</span>
                    <div>
                      <h3 className="text-xl font-medium tracking-[-0.015em]">{step.title}</h3>
                      <p className="mt-3 max-w-xl text-[15px] leading-7 text-muted-foreground">{step.body}</p>
                      <p className="mt-4 font-mono text-[11px] text-faint">{step.meta}</p>
                    </div>
                  </Reveal>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="sandboxes" className="scroll-mt-20 border-t border-border bg-card">
          <div className="mx-auto max-w-[1240px] px-4 py-16 sm:px-5 sm:py-24 md:px-8 lg:py-32">
            <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr] lg:items-end">
              <Reveal>
                <Eyebrow>Industry sandboxes</Eyebrow>
                <h2 className="mt-5 max-w-2xl text-[2rem] font-medium leading-[1.08] tracking-[-0.03em] sm:text-4xl md:text-5xl">
                  Fictional businesses with <span className="font-display italic text-muted-foreground">real boundaries.</span>
                </h2>
              </Reveal>
              <Reveal delay={0.05}>
                <p className="max-w-md text-[15px] leading-7 text-muted-foreground">
                  Each sandbox is a versioned, in-memory copy of synthetic records. Nothing an agent does inside one reaches a real system.
                </p>
              </Reveal>
            </div>

            <div className="mt-14 border-t border-border">
              {sandboxes.map((sandbox, i) => (
                <Reveal key={sandbox.name} delay={i * 0.04}>
                  <article className="grid gap-6 border-b border-border py-8 lg:grid-cols-[2.5rem_1fr_1.5fr]">
                    <span className="font-mono text-[12px] text-faint">{String(i + 1).padStart(2, "0")}</span>
                    <div>
                      <h3 className="text-2xl font-medium tracking-[-0.02em]">{sandbox.name}</h3>
                      <p className="mt-2 text-[14px] leading-6 text-muted-foreground">{sandbox.records}</p>
                      <p className="mt-4 font-mono text-[11px] text-faint">
                        default role <span className="text-muted-foreground">{sandbox.role}</span> · {sandbox.coverage}
                      </p>
                    </div>
                    <ul className="grid content-start gap-x-6 gap-y-2 font-mono text-[12px] text-muted-foreground sm:grid-cols-2">
                      {sandbox.tools.map((tool) => (
                        <li key={tool} className="flex items-center gap-2.5">
                          <span className="h-1 w-1 bg-faint" aria-hidden="true" />
                          {tool}
                        </li>
                      ))}
                    </ul>
                  </article>
                </Reveal>
              ))}
            </div>

            <div className="mt-10 flex flex-col gap-3 md:flex-row md:items-baseline md:gap-8">
              <p className="shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-faint">Not yet built</p>
              <p className="text-[14px] leading-7 text-muted-foreground">
                {planned.join(" · ")}. These are named so you know they are not available, not to suggest they are.
              </p>
            </div>
          </div>
        </section>

        <section id="regression" className="scroll-mt-20 border-t border-border">
          <div className="mx-auto max-w-[1240px] px-4 py-16 sm:px-5 sm:py-24 md:px-8 lg:py-32">
            <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
              <Reveal>
                <Eyebrow>Regression</Eyebrow>
                <h2 className="mt-5 text-[2rem] font-medium leading-[1.08] tracking-[-0.03em] sm:text-4xl md:text-5xl">
                  A fix is a claim. <span className="font-display italic text-muted-foreground">A rerun is evidence.</span>
                </h2>
              </Reveal>
              <Reveal delay={0.05}>
                <p className="max-w-xl text-[15px] leading-7 text-muted-foreground lg:ml-auto lg:pt-10">
                  Prompt changes, model upgrades, and new tools quietly reopen old weaknesses. Aegis compares each run to the baseline by test ID—so a break shows up as new, and a fix shows up as closed.
                </p>
              </Reveal>
            </div>

            <Reveal delay={0.1} className="mt-14">
              <RegressionStory />
            </Reveal>
          </div>
        </section>

        <section className="border-t border-border bg-card">
          <div className="mx-auto grid max-w-[1240px] gap-10 px-4 py-16 sm:gap-14 sm:px-5 sm:py-24 md:px-8 lg:grid-cols-[1fr_1.3fr] lg:py-32">
            <Reveal>
              <Eyebrow>Boundaries</Eyebrow>
              <h2 className="mt-5 text-[2rem] font-medium leading-[1.08] tracking-[-0.03em] sm:text-4xl md:text-5xl">
                What Aegis <span className="font-display italic text-muted-foreground">will not</span> tell you.
              </h2>
              <p className="mt-6 max-w-sm text-[15px] leading-7 text-muted-foreground">
                A security tool that overstates its findings is a liability. These limits are part of the product.
              </p>
            </Reveal>
            <ul className="border-t border-border">
              {refusals.map((line, i) => (
                <li key={line}>
                  <Reveal delay={i * 0.03} className="grid grid-cols-[2.5rem_1fr] border-b border-border py-5 text-[15px] leading-7">
                    <span aria-hidden="true" className="pt-px font-mono text-[12px] text-faint">—</span>
                    <span className="text-muted-foreground">{line}</span>
                  </Reveal>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[1240px] px-4 py-16 sm:px-5 sm:py-24 md:px-8 lg:py-36">
            <Reveal>
              <h2 className="max-w-4xl text-[clamp(2.4rem,5.5vw,4.5rem)] font-medium leading-[1.02] tracking-[-0.035em]">
                Run the accounting sandbox against the demonstration agent.{" "}
                <span className="font-display italic text-muted-foreground">It takes a few minutes.</span>
              </h2>
            </Reveal>
            <Reveal delay={0.08}>
              <div className="mt-10 flex flex-col gap-4 sm:mt-12 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-7">
                <Link href="/register" className="group inline-flex min-h-12 items-center justify-center gap-3 bg-foreground px-5 py-3 text-sm font-medium text-background transition-opacity hover:opacity-90 sm:min-h-0">
                  Create an organisation
                  <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">→</span>
                </Link>
                <Link href="/demo" className="text-sm underline decoration-input underline-offset-[6px] hover:decoration-foreground">
                  Read the walkthrough first
                </Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
