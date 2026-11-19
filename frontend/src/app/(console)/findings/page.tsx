import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { Panel, SectionHeader } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { serverApi } from "@/lib/api";
import { formatWhen, titleCase } from "@/lib/labels";
import type { Finding } from "@/lib/types";

export default async function FindingsPage() {
  const findings = await serverApi<Finding[]>("/findings");
  return (
    <div>
      <SectionHeader
        kicker="Evidence"
        title="Findings"
        description="Each finding records the observed evidence, a severity from published rules, and a status history. Not every failure is critical."
      />
      {findings.length === 0 ? (
        <EmptyState title="No findings recorded" body="When an assessment produces a finding, it will be listed here with its severity, status, and the agent it belongs to." />
      ) : (
        <Panel padded={false}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Recorded</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {findings.map((finding) => (
                <TableRow key={finding.id}>
                  <TableCell>
                    {finding.assessment_id ? (
                      <Link href={`/assessments/${finding.assessment_id}`} className="hover:text-signal">
                        {finding.title}
                      </Link>
                    ) : (
                      finding.title
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge tone={finding.severity}>{titleCase(finding.severity)}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge tone={finding.status}>{titleCase(finding.status)}</Badge>
                  </TableCell>
                  <TableCell>{formatWhen(finding.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
      )}
    </div>
  );
}
