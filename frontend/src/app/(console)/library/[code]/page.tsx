import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Kicker, RiskMark } from "@/components/intel/marks";
import { ApiNotFound, serverApi } from "@/lib/api";
import { scenarioCategoryLabels } from "@/lib/labels";
import type { ScenarioDetail } from "@/lib/types";

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  const { code } = await params;
  return { title: code };
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-border py-7">
      <Kicker>{title}</Kicker>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-border py-3">
      <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{label}</dt>
      <dd className="mt-1.5 text-[13px] leading-6 text-muted-foreground">{children}</dd>
    </div>
  );
}

export default async function ScenarioPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  let scenario: ScenarioDetail;
  try {
    scenario = await serverApi<ScenarioDetail>(`/scenario-library/${encodeURIComponent(code)}`);
  } catch (error) {
    if (error instanceof ApiNotFound) notFound();
    throw error;
  }

  return (
    <article>
      <Link href="/library" className="font-mono text-[11px] text-faint hover:text-muted-foreground">
        ← Scenario library
      </Link>
      <header className="mt-5 grid gap-6 border-b border-border pb-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <Kicker>
            {scenario.industry_name} · {scenario.code} · v{scenario.version}
          </Kicker>
          <h1 className="mt-3 max-w-3xl text-[30px] font-medium leading-tight tracking-[-0.025em]">{scenario.name}</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-7 text-muted-foreground">{scenario.description}</p>
        </div>
        <div className="flex items-center gap-6">
          <div>
            <Kicker>Risk</Kicker>
            <RiskMark risk={scenario.risk} className="mt-2" />
          </div>
          <div>
            <Kicker>Threat</Kicker>
            <p className="mt-2 font-mono text-[12px] text-foreground">{scenario.threat}</p>
          </div>
        </div>
      </header>

      <div className="grid gap-x-12 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="min-w-0">
          <Block title="Objective">
            <p className="max-w-2xl text-[15px] leading-7">{scenario.objective}</p>
          </Block>

          <Block title={`Simulated workflow · ${scenario.technique}`}>
            <div className="border border-border bg-card">
              <div className="border-b border-border px-4 py-3 text-[12px] leading-5 text-muted-foreground">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">Operator context</span>
                <p className="mt-1">{scenario.environment.context || "None beyond the sandbox rules."}</p>
              </div>
              <ol>
                {scenario.turns.map((turn, index) => (
                  <li key={turn} className="grid grid-cols-[4.5rem_1fr] gap-3 border-b border-border/70 px-4 py-3 last:border-b-0">
                    <span className="pt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-signal">User {index + 1}</span>
                    <p className="text-[14px] leading-6">{turn}</p>
                  </li>
                ))}
              </ol>
              <p className="border-t border-border px-4 py-3 text-[12px] leading-5 text-faint">
                The agent receives the sandbox tools. Every tool call is executed against synthetic data, the result is returned to the agent, and the loop continues for up to four tool rounds.
              </p>
            </div>
            {scenario.variants.length ? (
              <div className="mt-4">
                <p className="text-[12px] text-faint">Extended intensity also runs:</p>
                <ul className="mt-2 space-y-2">
                  {scenario.variants.map((variant, index) => (
                    <li key={index} className="border-l border-input pl-3 text-[13px] leading-6 text-muted-foreground">
                      {variant.join(" / ")}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Block>

          <Block title="Expected behaviour">
            <div className="grid gap-px border border-border bg-border md:grid-cols-2">
              <div className="bg-card p-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-success">Secure</p>
                <p className="mt-2 text-[14px] leading-6">{scenario.secure}</p>
              </div>
              <div className="bg-card p-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-destructive">Insecure</p>
                <p className="mt-2 text-[14px] leading-6">{scenario.insecure}</p>
              </div>
            </div>
          </Block>

          <Block title="Evaluation criteria">
            <ol className="space-y-2">
              {scenario.checks.map((check, index) => (
                <li key={index} className="grid grid-cols-[2rem_1fr] gap-2 text-[14px] leading-6">
                  <span className="font-mono text-[11px] text-faint">{String(index + 1).padStart(2, "0")}</span>
                  <span>
                    {check.description}
                    <span className="ml-2 font-mono text-[10px] text-faint">{check.kind}</span>
                  </span>
                </li>
              ))}
            </ol>
          </Block>

          <Block title="Scoring">
            <ul className="space-y-2 text-[13px] leading-6 text-muted-foreground">
              <li>{scenario.scoring.basis}</li>
              <li>{scenario.scoring.confidence}</li>
              <li>{scenario.scoring.outcomes}</li>
            </ul>
          </Block>

          <Block title="Remediation guidance">
            <ol className="space-y-2">
              {scenario.remediation.map((step, index) => (
                <li key={step} className="grid grid-cols-[2rem_1fr] gap-2 text-[14px] leading-6">
                  <span className="font-mono text-[11px] text-faint">{String(index + 1).padStart(2, "0")}</span>
                  {step}
                </li>
              ))}
            </ol>
          </Block>
        </div>

        <aside className="lg:sticky lg:top-20 lg:self-start lg:pt-7">
          <dl className="border-t border-border">
            <Meta label="Threat class">
              <span className="text-foreground">{scenario.threat_name}</span>
              <br />
              <span className="text-[12px] text-faint">{scenario.threat_reference}</span>
            </Meta>
            <Meta label="Category">{scenarioCategoryLabels[scenario.category] ?? scenario.category}</Meta>
            <Meta label="Environment">
              {scenario.sandbox_name}
              <br />
              <span className="font-mono text-[12px]">role {scenario.environment.role}</span>
            </Meta>
            <Meta label="Datasets">{scenario.environment.datasets.join(", ")}</Meta>
            <Meta label="Tools under test">
              <span className="font-mono text-[12px]">{scenario.environment.tools.length ? scenario.environment.tools.join(", ") : "Text only"}</span>
            </Meta>
            <Meta label="Applies when the agent">{scenario.exposure_labels.join("; ")}</Meta>
            <Meta label="Preconditions">
              <ul className="space-y-1">
                {scenario.preconditions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Meta>
            <Meta label="Definition hash">
              <span className="break-all font-mono text-[11px] text-faint">{scenario.content_hash}</span>
            </Meta>
          </dl>
        </aside>
      </div>
    </article>
  );
}
