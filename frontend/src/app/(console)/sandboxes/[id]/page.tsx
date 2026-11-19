import { LabWorkspace } from "@/components/simulation/lab-workspace";
import { serverApi } from "@/lib/api";
import type { SandboxDetail } from "@/lib/types";

export default async function SandboxEnvironmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sandbox = await serverApi<SandboxDetail>(`/sandboxes/${id}`);
  return <LabWorkspace sandbox={sandbox} />;
}
