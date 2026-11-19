import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProfileEditor } from "@/components/intel/profile-editor";
import { PageHeader } from "@/components/page-header";
import { ApiNotFound, serverApi } from "@/lib/api";
import type { Agent, AgentProfile, LibraryIndex } from "@/lib/types";

export const metadata: Metadata = { title: "Agent profile" };

export default async function AgentProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let agent: Agent;
  try {
    agent = await serverApi<Agent>(`/agents/${id}`);
  } catch (error) {
    if (error instanceof ApiNotFound) notFound();
    throw error;
  }
  const [{ profile }, index] = await Promise.all([
    serverApi<{ profile: AgentProfile | null }>(`/agents/${id}/profile`),
    serverApi<LibraryIndex>("/scenario-library"),
  ]);
  return (
    <div>
      <Link href={`/agents/${id}`} className="font-mono text-[11px] text-faint hover:text-muted-foreground">
        ← {agent.name}
      </Link>
      <div className="mt-4">
        <PageHeader
          kicker="Agent profiling"
          title={profile ? "Security profile" : "Profile this agent"}
          description="Tell Aegis what this agent is for and what it can touch. The profile decides which industry scenarios apply and how they are prioritised."
        />
      </div>
      <ProfileEditor agentId={id} agentName={agent.name} profile={profile} index={index} />
    </div>
  );
}
