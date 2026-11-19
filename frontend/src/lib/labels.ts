export const integrationTypes = [
  { value: "openai_compatible", label: "OpenAI-compatible" },
  { value: "anthropic", label: "Anthropic (adapter not implemented)" },
  { value: "azure_openai", label: "Azure OpenAI (adapter not implemented)" },
  { value: "amazon_bedrock", label: "Amazon Bedrock (adapter not implemented)" },
  { value: "custom_http", label: "Custom HTTP (adapter not implemented)" },
] as const;

export const assessmentCategories = [
  ["prompt_injection", "Prompt injection"],
  ["system_disclosure", "System instruction disclosure"],
  ["sensitive_data_leakage", "Synthetic data leakage"],
  ["instruction_hierarchy", "Instruction hierarchy"],
  ["unauthorised_tool_use", "Unauthorised tool use"],
  ["cross_user_exposure", "Cross-user exposure"],
  ["privilege_escalation", "Privilege escalation"],
  ["unsafe_output", "Unsafe output"],
  ["data_exfiltration", "Data exfiltration"],
  ["insecure_workflow", "Insecure workflow"],
] as const;

export const scenarioCategoryLabels: Record<string, string> = {
  ...Object.fromEntries(assessmentCategories),
  social_engineering: "Social engineering",
  output_integrity: "Output integrity",
};

export const riskOrder = ["critical", "high", "medium", "low"] as const;

export const riskTone: Record<string, string> = {
  critical: "text-destructive",
  high: "text-signal",
  medium: "text-foreground",
  low: "text-muted-foreground",
  informational: "text-faint",
};

export const outcomeTone: Record<string, string> = {
  PASS: "text-success",
  FAIL: "text-destructive",
  INCONCLUSIVE: "text-signal",
  ERROR: "text-muted-foreground",
  SKIPPED: "text-faint",
};

export const outcomeFill: Record<string, string> = {
  PASS: "bg-success",
  FAIL: "bg-destructive",
  INCONCLUSIVE: "bg-signal",
  ERROR: "bg-muted-foreground",
  SKIPPED: "bg-faint",
};

export function integrationLabel(value: string) {
  if (value === "aegis_demo") return "Aegis demo";
  return integrationTypes.find((item) => item.value === value)?.label ?? value;
}

export function formatWhen(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
