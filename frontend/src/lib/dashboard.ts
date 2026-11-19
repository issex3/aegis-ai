import type { DashboardSummary } from "@/lib/types";

export function hasAssessmentActivity(summary: DashboardSummary) {
  return summary.assessments.total > 0 || summary.findings.total > 0;
}

export function showSeverityChart(summary: DashboardSummary) {
  return summary.findings.total > 0 && Object.keys(summary.findings.by_severity).length > 0;
}

export function showAssessmentChart(summary: DashboardSummary) {
  return summary.assessments.total > 0 && Object.keys(summary.assessments.by_status).length > 0;
}

export function countEntries(record: Record<string, number>) {
  return Object.entries(record).map(([name, count]) => ({ name, count }));
}
