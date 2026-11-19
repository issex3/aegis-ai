import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProgrammeBuilder } from "@/components/intel/programme-builder";
import { PageHeader } from "@/components/page-header";
import { ApiNotFound, serverApi } from "@/lib/api";
import type { Programme } from "@/lib/types";

export const metadata: Metadata = { title: "Testing programme" };

export default async function ProgrammePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let programme: Programme;
  try {
    programme = await serverApi<Programme>(`/programmes/${id}`);
  } catch (error) {
    if (error instanceof ApiNotFound) notFound();
    throw error;
  }
  return (
    <div>
      <Link href="/programmes" className="font-mono text-[11px] text-faint hover:text-muted-foreground">
        ← Programmes
      </Link>
      <div className="mt-4">
        <PageHeader
          kicker={`Testing programme · ${programme.industry_name}`}
          title={programme.agent_name}
          description="Scenarios were selected from the profile and ranked by risk. Review the selection, adjust intensity, and launch."
        />
      </div>
      <ProgrammeBuilder initial={programme} />
    </div>
  );
}
