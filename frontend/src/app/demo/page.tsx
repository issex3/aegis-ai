import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = {
  title: "Demonstration",
  description: "Run a real assessment against Aegis's built-in demonstration agent in a synthetic sandbox. No API key required.",
};

const steps = [
  { title: "Create an organisation", body: "Register, or sign in to an existing workspace. The first account becomes the owner." },
  { title: "Add the demonstration agent", body: "In Agents, add the built-in demo agent. It runs locally and calls no external model." },
  { title: "Profile it and build a programme", body: "In Programmes, describe the agent and pick an industry. Aegis selects and ranks the scenarios that apply, and you review them before anything runs." },
  { title: "Run, inspect, export", body: "Launch the programme, follow the execution log, open each scenario's transcript and evidence, and generate the PDF report." },
];

const profiles = [
  { name: "default", body: "Follows instructions containing trigger phrases and requests any tool named in the prompt. Most boundary cases fail." },
  { name: "regressed", body: "Behaves like default but also leaks CANARY-REGRESSION-900, so the control case fails. Use it to see a new vulnerability flagged against a baseline." },
  { name: "remediated", body: "Declines every request and calls no tools. Use it to see findings marked as resolved." },
];

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-[1240px] px-5 md:px-8">
        <section className="grid gap-12 py-16 lg:grid-cols-[1.2fr_1fr] lg:py-24">
          <div>
            <p className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              <span className="h-px w-8 bg-signal" />
              Demonstration
            </p>
            <h1 className="mt-8 text-[clamp(2.4rem,5vw,4rem)] font-medium leading-[1.03] tracking-[-0.035em]">
              A local agent with <span className="font-display italic text-muted-foreground">deliberate weaknesses.</span>
            </h1>
          </div>
          <div className="lg:pt-16">
            <p className="text-[15px] leading-7 text-muted-foreground">
              The tests actually run. The agent under test is simulated. Its findings are planted weaknesses, not incidents from a customer environment, and every result it produces is labelled as simulated. No external API key is required.
            </p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-7">
              <Link href="/register" className="inline-flex min-h-12 items-center justify-center gap-3 bg-foreground px-5 py-3 text-sm font-medium text-background transition-opacity hover:opacity-90 sm:min-h-0">
                Create an organisation <span aria-hidden="true">→</span>
              </Link>
              <Link href="/login" className="text-sm underline decoration-input underline-offset-[6px] hover:decoration-foreground">
                Sign in
              </Link>
            </div>
          </div>
        </section>

        <section aria-labelledby="steps" className="border-t border-border py-16">
          <h2 id="steps" className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">
            Four steps
          </h2>
          <ol className="mt-8 grid border-t border-border md:grid-cols-4">
            {steps.map((step, i) => (
              <li key={step.title} className={`py-7 md:px-6 md:first:pl-0 ${i > 0 ? "border-t border-border md:border-t-0 md:border-l" : ""}`}>
                <span className="font-mono text-[12px] text-signal">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="mt-4 text-lg font-medium tracking-[-0.01em]">{step.title}</h3>
                <p className="mt-2 text-[14px] leading-6 text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="profiles" className="grid gap-10 border-t border-border py-16 lg:grid-cols-[1fr_2fr] lg:py-24">
          <div>
            <h2 id="profiles" className="text-3xl font-medium tracking-[-0.025em]">
              Three behaviour profiles
            </h2>
            <p className="mt-4 max-w-sm text-[14px] leading-6 text-muted-foreground">
              Set the profile on the demo agent to exercise baselines, regressions, and retests without a real model.
            </p>
          </div>
          <dl className="border-t border-border">
            {profiles.map((profile) => (
              <div key={profile.name} className="grid gap-2 border-b border-border py-6 md:grid-cols-[10rem_1fr]">
                <dt className="font-mono text-[13px] text-foreground">{profile.name}</dt>
                <dd className="text-[14px] leading-6 text-muted-foreground">{profile.body}</dd>
              </div>
            ))}
          </dl>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
