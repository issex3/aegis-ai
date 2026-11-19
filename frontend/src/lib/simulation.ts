import type { SandboxCatalogueItem } from "@/lib/types";

export type LabEnvironmentKey =
  | "accounting"
  | "healthcare"
  | "legal"
  | "retail"
  | "customer_service"
  | "sales_crm";

export const LAB_ORDER: LabEnvironmentKey[] = [
  "accounting",
  "healthcare",
  "legal",
  "retail",
  "customer_service",
  "sales_crm",
];

export const LAB_IDENTITY: Record<
  LabEnvironmentKey,
  { label: string; accentClass: string; accentVar: string; blurb: string }
> = {
  accounting: {
    label: "Accounting",
    accentClass: "text-lab-accounting",
    accentVar: "var(--lab-accounting)",
    blurb: "Bookkeeping, invoices, payroll boundaries, and two-step payment approval.",
  },
  healthcare: {
    label: "Healthcare",
    accentClass: "text-lab-healthcare",
    accentVar: "var(--lab-healthcare)",
    blurb: "Outpatient clinic records, appointments, and patient-message controls.",
  },
  legal: {
    label: "Legal",
    accentClass: "text-lab-legal",
    accentVar: "var(--lab-legal)",
    blurb: "Matter confidentiality, document permissions, and privileged material.",
  },
  retail: {
    label: "Retail",
    accentClass: "text-lab-retail",
    accentVar: "var(--lab-retail)",
    blurb: "Orders, inventory, refunds, and customer-scoped support actions.",
  },
  customer_service: {
    label: "Customer Service",
    accentClass: "text-lab-customer-service",
    accentVar: "var(--lab-customer-service)",
    blurb: "Account lookup, refunds, escalation, and policy-bound support tools.",
  },
  sales_crm: {
    label: "Sales CRM",
    accentClass: "text-lab-sales-crm",
    accentVar: "var(--lab-sales-crm)",
    blurb: "Contacts, deals, discounts, and outbound commercial messaging.",
  },
};

export function resolveLabKey(item: Pick<SandboxCatalogueItem, "slug" | "industry_slug" | "name" | "industry_name">): LabEnvironmentKey | null {
  const slug = (item.slug || item.industry_slug || "").toLowerCase();
  if (slug in LAB_IDENTITY) return slug as LabEnvironmentKey;
  const haystack = `${item.name} ${item.industry_name}`.toLowerCase();
  if (haystack.includes("account")) return "accounting";
  if (haystack.includes("health")) return "healthcare";
  if (haystack.includes("legal")) return "legal";
  if (haystack.includes("retail")) return "retail";
  if (haystack.includes("customer") || haystack.includes("support")) return "customer_service";
  if (haystack.includes("sales") || haystack.includes("crm")) return "sales_crm";
  return null;
}

export function sortLabCatalogue(items: SandboxCatalogueItem[]) {
  return [...items].sort((a, b) => {
    const ak = resolveLabKey(a);
    const bk = resolveLabKey(b);
    const ai = ak ? LAB_ORDER.indexOf(ak) : 99;
    const bi = bk ? LAB_ORDER.indexOf(bk) : 99;
    return ai - bi || a.name.localeCompare(b.name);
  });
}

export function recordsFromMap<T extends Record<string, unknown>>(value: unknown): T[] {
  if (!value || typeof value !== "object") return [];
  return Object.values(value as Record<string, T>);
}
