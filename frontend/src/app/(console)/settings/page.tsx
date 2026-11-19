import { Kicker, Panel, SectionHeader } from "@/components/layout";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SettingsForms } from "@/components/workspace-forms";
import { serverApi } from "@/lib/api";
import { formatWhen, titleCase } from "@/lib/labels";
import type { AuditEvent, Session } from "@/lib/types";

export default async function SettingsPage() {
  const session = await serverApi<Session>("/auth/me");
  const canAudit = session.role === "owner" || session.role === "admin" || session.role === "administrator";
  const events = canAudit ? await serverApi<AuditEvent[]>("/audit-events") : [];
  return (
    <div>
      <SectionHeader kicker="Account" title="Settings" description="Profile, password, organisation name, and the recent audit trail for this organisation." />
      <SettingsForms session={session} />
      <Panel className="mt-4" padded={false}>
        <div className="border-b border-border px-4 py-3">
          <Kicker>Audit</Kicker>
          <h2 className="mt-1 text-[15px] font-medium">Audit trail</h2>
        </div>
        {events.length === 0 ? (
          <p className="px-4 py-6 text-[13px] text-muted-foreground">No audit events recorded.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="font-mono text-xs">{event.action}</TableCell>
                  <TableCell>{titleCase(event.resource_type)}</TableCell>
                  <TableCell>{formatWhen(event.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
    </div>
  );
}
