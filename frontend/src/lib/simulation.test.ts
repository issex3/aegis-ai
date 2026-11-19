import { describe, expect, it } from "vitest";
import { resolveLabKey, sortLabCatalogue } from "@/lib/simulation";
import type { SandboxCatalogueItem } from "@/lib/types";

function item(partial: Partial<SandboxCatalogueItem> & Pick<SandboxCatalogueItem, "id" | "name" | "industry_name">): SandboxCatalogueItem {
  return {
    description: "",
    status: "available",
    current_version_number: 1,
    availability: "available",
    scenario_count: 0,
    categories: [],
    tools: [],
    workflows: [],
    updated_at: null,
    ...partial,
  };
}

describe("simulation lab catalogue helpers", () => {
  it("resolves environment keys from slugs", () => {
    expect(resolveLabKey(item({ id: "1", name: "Accounting operations", industry_name: "Accounting", slug: "accounting" }))).toBe("accounting");
    expect(resolveLabKey(item({ id: "2", name: "Sales CRM workspace", industry_name: "Sales", slug: "sales_crm" }))).toBe("sales_crm");
  });

  it("sorts environments into the Simulation Lab order", () => {
    const sorted = sortLabCatalogue([
      item({ id: "r", name: "Retail support desk", industry_name: "Retail", slug: "retail" }),
      item({ id: "a", name: "Accounting operations", industry_name: "Accounting", slug: "accounting" }),
      item({ id: "h", name: "Outpatient clinic services", industry_name: "Healthcare", slug: "healthcare" }),
    ]);
    expect(sorted.map((row) => row.slug)).toEqual(["accounting", "healthcare", "retail"]);
  });
});
