import type { Metadata } from "next";
import { LibraryBrowser } from "@/components/intel/library-browser";
import { SectionHeader } from "@/components/layout";
import { serverApi } from "@/lib/api";
import type { LibraryIndex } from "@/lib/types";

export const metadata: Metadata = { title: "Scenario library" };

export default async function LibraryPage() {
  const index = await serverApi<LibraryIndex>("/scenario-library");
  return (
    <div>
      <SectionHeader
        kicker="Industry intelligence"
        title="Scenario library"
        description="Structured, versioned attack scenarios for each industry. Programmes select from this library based on what an agent actually does."
      />
      <LibraryBrowser index={index} />
    </div>
  );
}
