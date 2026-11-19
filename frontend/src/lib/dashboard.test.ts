import { describe, expect, it } from "vitest";
import { hasAssessmentActivity, showAssessmentChart, showSeverityChart } from "@/lib/dashboard";
import type { DashboardSummary } from "@/lib/types";

function summary(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    agents: { total: 0, active: 0, disabled: 0 },
    assessments: { total: 0, by_status: {} },
    findings: { total: 0, open: 0, by_severity: {} },
    reports: { total: 0 },
    recent_assessments: [],
    recent_audit_events: [],
    ...overrides,
  };
}

describe("dashboard presentation", () => {
  it("does not treat an empty organisation as assessment activity", () => {
    const data = summary();
    expect(hasAssessmentActivity(data)).toBe(false);
    expect(showAssessmentChart(data)).toBe(false);
    expect(showSeverityChart(data)).toBe(false);
  });

  it("shows charts only when the underlying records exist", () => {
    const data = summary({
      agents: { total: 1, active: 1, disabled: 0 },
      assessments: { total: 2, by_status: { draft: 2 } },
      findings: { total: 1, open: 1, by_severity: { high: 1 } },
    });
    expect(hasAssessmentActivity(data)).toBe(true);
    expect(showAssessmentChart(data)).toBe(true);
    expect(showSeverityChart(data)).toBe(true);
  });
});
