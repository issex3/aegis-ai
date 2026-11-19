export type Session = {
  user: {
    id: string;
    email: string;
    full_name: string;
    is_platform_operator: boolean;
    mfa_enabled?: boolean;
  };
  organisation: {
    id: string;
    name: string;
    slug: string;
    retention_days?: number;
  };
  role: string;
};

export type MfaChallenge = {
  mfa_required: true;
  challenge_id: string;
};

export type Credential = {
  configured: boolean;
  hint: string | null;
  updated_at: string | null;
};

export type Agent = {
  id: string;
  name: string;
  description: string;
  integration_type: string;
  api_endpoint: string;
  model_name: string;
  purpose: string;
  behaviour: string;
  security_boundaries: string;
  status: "active" | "disabled";
  created_at: string;
  updated_at: string;
  credential: Credential;
  timeout_seconds: number;
  max_output_tokens: number;
  temperature: number | null;
  adapter_status: "runnable" | "demo" | "not_implemented" | string;
  demo_profile?: "default" | "regressed" | "remediated" | null;
};

export type Assessment = {
  id: string;
  agent_id: string;
  agent_name: string;
  name: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type AssessmentResult = {
  id: string;
  code: string | null;
  title: string;
  category: string | null;
  version: string | null;
  outcome: string;
  summary: string;
  duration_ms: number | null;
  created_at: string;
  evidence: {
    engine?: "scenario";
    scenario?: { code: string; result_code: string; version: string; content_hash?: string; name?: string; threat?: string; risk?: string; variant: number };
    transcript?: { role: string; content?: string | null; tool?: string; allowed?: boolean; policy?: string; tool_calls?: { name: string; arguments: Record<string, unknown> }[] }[];
    checks?: { kind: string; description: string; status: "pass" | "fail" | "inconclusive"; detail: string; confidence: string }[];
    state_changes?: { path: string; before: unknown; after: unknown }[];
    reproduction?: { sandbox: string; role: string; context: string; turns: string[]; scenario_version: string; content_hash: string };
    insecure_behaviour?: string;
    actual_behaviour?: string;
    confidence?: string | null;
    tool_channel?: string;
    input?: string;
    expected_behaviour?: string;
    observable_response?: string;
    tool_calls?: { name: string; arguments: Record<string, string> }[];
    sandbox_tool_events?: { tool: string; allowed: boolean; role: string; policy: string }[];
    limitations?: string[];
    simulated?: boolean;
    error_code?: string | null;
  };
};

export type AssessmentDetail = Assessment & {
  is_simulated: boolean;
  engine?: "catalogue" | "scenario";
  programme_id?: string | null;
  planned?: number;
  simulated_role: string | null;
  selected_categories: string[];
  error_summary: string;
  cancel_requested: boolean;
  counts: Record<string, number>;
  results: AssessmentResult[];
  score?: {
    score: number | null;
    classification: string;
    applicable_tests: number;
    inconclusive: number;
    confidence: number;
    coverage: number;
    disclaimer: string;
  };
};

export type SandboxDetail = {
  id: string;
  name: string;
  description: string;
  status: string;
  version_number: number | null;
  slug?: string | null;
  industry_slug?: string | null;
  industry_name?: string | null;
  boundaries: string;
  default_role: string | null;
  roles?: string[];
  datasets: { name: string; description: string }[];
  tools: { name: string; description: string; roles: string[]; deny_policy: string | null }[];
  workflows: { name: string; description: string }[];
  scenarios: { code: string; title: string; category: string; severity: string; requires_tools: boolean }[];
  data_classes?: { key: string; label: string }[];
  limitation: string;
  updated_at?: string | null;
  version_history?: { version: number; status: string; changelog: string }[];
};

export type LabTool = {
  name: string;
  description: string;
  roles: string[];
  deny_policy: string;
  allow_policy: string;
  params: Record<string, string>;
};

export type LabEvent = {
  sequence: number;
  tool: string;
  arguments: Record<string, unknown>;
  allowed: boolean;
  role: string;
  policy: string;
  output: Record<string, unknown> | null;
};

export type LabGraph = {
  nodes: { id: string; type: string; label: string; data: Record<string, unknown> }[];
  edges: { id: string; source: string; target: string; label?: string; data?: Record<string, unknown> }[];
};

export type LabSession = {
  id: string;
  sandbox_id: string;
  slug: string;
  role: string;
  status: string;
  created_at: number;
  touched_at: number;
  state: Record<string, unknown>;
  initial_state: Record<string, unknown>;
  events: LabEvent[];
  stats: { tool_calls: number; allowed: number; denied: number };
  tools: LabTool[];
  roles: string[];
  graph: LabGraph;
  limitation: string;
  last_event?: LabEvent;
};

export type SandboxCatalogueItem = {
  id: string;
  name: string;
  description: string;
  industry_name: string;
  status: string;
  current_version_number: number | null;
  availability: "available";
  slug?: string | null;
  industry_slug?: string | null;
  scenario_count: number;
  categories: string[];
  tools: string[];
  workflows: string[];
  datasets?: string[];
  roles?: string[];
  data_classes?: { key: string; label: string }[];
  default_role?: string | null;
  boundaries?: string;
  updated_at: string | null;
  limitation?: string;
};

export type Finding = {
  id: string;
  title: string;
  severity: string;
  status: string;
  agent_id: string;
  assessment_id: string;
  created_at: string;
};

export type Report = {
  id: string;
  title: string;
  status: string;
  assessment_id: string | null;
  created_at: string;
};

export type Industry = {
  id: string;
  slug: string;
  name: string;
  description: string;
};

export type Sandbox = {
  id: string;
  name: string;
  description: string;
  status: string;
  industry_name: string;
  current_version_number: number | null;
};

export type AuditEvent = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  created_at: string;
};

export type Consent = {
  granted: boolean;
  policy_version: string;
  scope: string;
  recorded_at: string | null;
};

export type DashboardSummary = {
  agents: { total: number; active: number; disabled: number };
  assessments: { total: number; by_status: Record<string, number> };
  findings: { total: number; open: number; by_severity: Record<string, number> };
  reports: { total: number };
  recent_assessments: Assessment[];
  recent_audit_events: AuditEvent[];
  posture?: {
    score: number | null;
    classification: string;
    applicable_tests: number;
    inconclusive: number;
    errors: number;
    coverage: number;
    confidence: number;
    disclaimer: string;
    history: { assessment_id: string; name: string; score: number | null }[];
    findings_by_severity: Record<string, number>;
    findings_by_sandbox: Record<string, number>;
    resolved: number;
    regression: Record<string, number>;
    baselines: number;
  } | null;
};

export type RiskLevel = "critical" | "high" | "medium" | "low";

export type ScenarioSummary = {
  code: string;
  version: string;
  name: string;
  industry: string;
  category: string;
  threat: string;
  threat_name: string;
  risk: RiskLevel;
  description: string;
  technique: string;
  exposure: string[];
  sandbox: string;
  variants: number;
};

export type LibraryIndustry = {
  slug: string;
  name: string;
  summary: string;
  sandbox: string;
  sandbox_name: string;
  scenarios: number;
  by_risk: Record<RiskLevel, number>;
  threats: string[];
  typical_capabilities: string[];
  typical_data: string[];
};

export type LibraryIndex = {
  industries: LibraryIndustry[];
  threats: { key: string; name: string; reference: string }[];
  categories: string[];
  capabilities: { key: string; label: string; kind: "surface" | "data" | "action" }[];
  data_classes: { key: string; label: string }[];
  intensities: Record<string, string>;
  scenarios: ScenarioSummary[];
};

export type ScenarioCheck = {
  kind: string;
  description: string;
  tools: string[];
  target: string | null;
  markers: string[];
  paths: string[];
  patterns: string[];
  correct: string[];
};

export type ScenarioDetail = Omit<ScenarioSummary, "variants"> & {
  objective: string;
  preconditions: string[];
  environment: { sandbox: string; role: string; datasets: string[]; tools: string[]; context: string };
  turns: string[];
  secure: string;
  insecure: string;
  checks: ScenarioCheck[];
  evaluation_criteria: string[];
  scoring: { weight: number; basis: string; confidence: string; outcomes: string };
  remediation: string[];
  data_classes: string[];
  variants: string[][];
  requires_tools: boolean;
  threat_reference: string;
  industry_name: string;
  sandbox_name: string;
  sandbox_boundaries: string;
  exposure_labels: string[];
  content_hash: string;
};

export type CapabilityInference = {
  key: string;
  label: string;
  kind: "surface" | "data" | "action";
  evidence: { field: string; term: string }[];
  typical_for_industry: boolean;
};

export type ProfileAnalysis = {
  method: string;
  capabilities: CapabilityInference[];
  data_classes: { key: string; label: string; source: string }[];
  missing_typical: { key: string; label: string }[];
  action_capabilities: number;
};

export type AgentProfile = {
  id: string;
  agent_id: string;
  industry: string;
  description: string;
  purpose: string;
  responsibilities: string[];
  tools: string[];
  permissions: string[];
  data_types: string[];
  authorised_actions: string[];
  risk_sensitivity: "low" | "moderate" | "high" | "critical";
  capabilities: string[];
  analysis: ProfileAnalysis;
  version: number;
  updated_at: string;
};

export type SelectionEntry = {
  code: string;
  version: string;
  name: string;
  category: string;
  threat: string;
  threat_name: string;
  risk: RiskLevel;
  applicable: boolean;
  matched_capabilities: string[];
  priority_points: number;
  priority: "P1" | "P2" | "P3" | null;
  rationale: string[];
  reason: string | null;
  variants: number;
  selected: boolean;
  override: boolean;
};

export type Programme = {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_simulated: boolean;
  industry: string;
  industry_name: string;
  profile_version: number;
  intensity: "focused" | "standard" | "extended";
  intensities: Record<string, string>;
  include_generic: boolean;
  generic_categories: string[];
  status: string;
  selection: SelectionEntry[];
  profile: {
    industry: string;
    version: number;
    capabilities: { key: string; label: string }[];
    data_classes: { key: string; label: string }[];
    risk_sensitivity: string;
    purpose: string;
  };
  stats: {
    library: number;
    applicable: number;
    not_applicable: number;
    selected: number;
    overrides: number;
    executions: number;
    generic: number;
    threats: Record<string, { name: string; applicable: number; selected: number }>;
    by_priority: Record<string, number>;
  };
  runs: { id: string; name: string; status: string; created_at: string }[];
  created_at: string;
  updated_at: string;
};

export type ExecutionLogEntry = {
  sequence: number;
  level: "info" | "warning" | "error";
  event: string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
};

export type ScoreBlock = {
  score: number | null;
  classification: string;
  applicable_tests: number;
  passed: number;
  failed: number;
  inconclusive: number;
  errors: number;
  skipped: number;
  penalty: number;
  maximum_points: number;
};

export type OutcomeTally = { key: string; label: string; PASS: number; FAIL: number; INCONCLUSIVE: number; ERROR: number; SKIPPED: number };

export type IntelligenceRow = {
  id: string;
  code: string | null;
  scenario_code: string | null;
  kind: "scenario" | "generic";
  title: string;
  threat: string | null;
  category: string | null;
  risk: string | null;
  outcome: string;
  severity: string | null;
  finding_id: string | null;
  summary: string;
  variant: number;
};

export type IntelligenceReport = {
  assessment_id: string;
  status: string;
  is_simulated: boolean;
  industry: string;
  industry_name: string;
  intensity: string;
  profile: Programme["profile"];
  overall_score: ScoreBlock;
  industry_score: ScoreBlock;
  generic_score: ScoreBlock | null;
  outcomes: Record<string, number>;
  by_threat: OutcomeTally[];
  by_risk: OutcomeTally[];
  critical: { code: string; title: string; summary: string; finding_id: string | null; threat: string | null }[];
  remediation: { step: string; severity: string | null; source: string }[];
  coverage: {
    planned: number;
    recorded: number;
    executed: number;
    inconclusive: number;
    could_not_execute: number;
    library_size: number;
    threats_tested: string[];
    threats_in_library: string[];
  };
  rows: IntelligenceRow[];
  comparison: {
    previous_id: string;
    previous_name: string;
    previous_score: number | null;
    score_delta: number | null;
    counts: Record<string, number>;
    changes: { code: string; status: string; baseline_outcome: string | null; current_outcome: string | null }[];
  } | null;
  definitions: Record<string, string>;
  disclaimer: string;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: { field: string; message: string }[];
  };
};
