import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { Panel, SectionHeader } from "@/components/layout";
import { ReportRowActions } from "@/components/report-actions";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { serverApi } from "@/lib/api";
import { formatWhen, titleCase } from "@/lib/labels";
import type { Report } from "@/lib/types";

export default async function ReportsPage() {
  const reports = await serverApi<Report[]>("/reports");
  return (
    <div>
      <SectionHeader
        kicker="Delivery"
        title="Reports"
        description="PDFs are generated from a completed assessment. They separate observations, simulated tool results, and inferred severity."
      />
      {reports.length === 0 ? (
        <EmptyState
          title="No reports"
          body="Finish an assessment, then generate a PDF from the assessment page."
          action={
            <Button asChild variant="outline">
              <Link href="/programmes">Open programmes</Link>
            </Button>
          }
        />
      ) : (
        <Panel padded={false}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell>
                    {report.assessment_id ? (
                      <Link href={`/assessments/${report.assessment_id}`} className="hover:text-signal">
                        {report.title}
                      </Link>
                    ) : (
                      report.title
                    )}
                  </TableCell>
                  <TableCell>{titleCase(report.status)}</TableCell>
                  <TableCell>{formatWhen(report.created_at)}</TableCell>
                  <TableCell>
                    <ReportRowActions reportId={report.id} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
      )}
    </div>
  );
}
