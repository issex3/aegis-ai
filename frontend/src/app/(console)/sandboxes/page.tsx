import { LabCatalogue } from "@/components/simulation/lab-catalogue";
import { serverApi } from "@/lib/api";
import type { SandboxCatalogueItem } from "@/lib/types";

type Planned = { name: string; status: string; description: string };

export default async function SimulationLabPage() {
  const catalogue = await serverApi<{ available: SandboxCatalogueItem[]; planned: Planned[] }>("/sandbox-catalogue");
  return <LabCatalogue available={catalogue.available} planned={catalogue.planned} />;
}
