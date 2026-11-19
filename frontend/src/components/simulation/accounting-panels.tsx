"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { DataTable, researchTableFeatures } from "@/components/data/data-table";
import { Kicker } from "@/components/layout";
import { recordsFromMap } from "@/lib/simulation";
import { cn } from "@/lib/utils";

type Invoice = { id: string; client_id: string; amount: string; description?: string; vat_rate?: string };
type Client = { id: string; name: string; token?: string };
type Payment = { id?: string; invoice_id: string; status: string; amount?: string };
type Supplier = { id: string; name: string; client_id: string; bank?: string };
type Journal = { amount: string; memo?: string; reference?: string };
type Employee = { id: string; name: string; title?: string };
type Payroll = { id: string; token?: string; amount?: string };
type Inbox = { id: string; client_id?: string; from?: string; subject?: string; body?: string };

const invoiceColumns: Array<ColumnDef<typeof researchTableFeatures, Invoice>> = [
  { accessorKey: "id", header: "Invoice", enableSorting: true },
  { accessorKey: "client_id", header: "Client", enableSorting: true },
  { accessorKey: "amount", header: "Amount", enableSorting: true },
  {
    accessorKey: "description",
    header: "Description",
    cell: (info) => <span className="line-clamp-2 max-w-md text-muted-foreground">{String(info.getValue() ?? "")}</span>,
  },
];

const clientColumns: Array<ColumnDef<typeof researchTableFeatures, Client>> = [
  { accessorKey: "id", header: "Account", enableSorting: true },
  { accessorKey: "name", header: "Name", enableSorting: true },
  {
    accessorKey: "token",
    header: "Sensitive marker",
    cell: (info) => <span className="font-mono text-[11px] text-cyan">{String(info.getValue() ?? "—")}</span>,
  },
];

const paymentColumns: Array<ColumnDef<typeof researchTableFeatures, Payment & { id: string }>> = [
  { accessorKey: "id", header: "Payment", enableSorting: true },
  { accessorKey: "invoice_id", header: "Invoice", enableSorting: true },
  { accessorKey: "amount", header: "Amount", enableSorting: true },
  {
    accessorKey: "status",
    header: "Approval",
    enableSorting: true,
    cell: (info) => {
      const status = String(info.getValue());
      return (
        <span
          className={cn(
            "font-mono text-[11px] uppercase",
            status === "approved" ? "text-success" : status === "draft" ? "text-warning" : "text-signal",
          )}
        >
          {status}
        </span>
      );
    },
  },
];

const supplierColumns: Array<ColumnDef<typeof researchTableFeatures, Supplier>> = [
  { accessorKey: "id", header: "Supplier", enableSorting: true },
  { accessorKey: "name", header: "Name", enableSorting: true },
  { accessorKey: "client_id", header: "Client", enableSorting: true },
  {
    accessorKey: "bank",
    header: "Bank ref",
    cell: (info) => <span className="font-mono text-[11px] text-warning">{String(info.getValue() ?? "—")}</span>,
  },
];

const journalColumns: Array<ColumnDef<typeof researchTableFeatures, Journal & { id: string }>> = [
  { accessorKey: "id", header: "Entry", enableSorting: true },
  { accessorKey: "amount", header: "Amount", enableSorting: true },
  { accessorKey: "memo", header: "Memo" },
  { accessorKey: "reference", header: "Reference" },
];

/** Financial-ops workbench summary — World pane. */
export function AccountingOverview({ state }: { state: Record<string, unknown> }) {
  const ledger = (state.ledger ?? {}) as { period?: string; revenue?: string; expenses?: string };
  const payments = recordsFromMap<Payment>(state.payments);
  const invoices = recordsFromMap<Invoice>(state.invoices);
  const journal = recordsFromMap<Journal>(state.journal);
  const inbox = recordsFromMap<Inbox>(state.inbox);
  const approved = payments.filter((row) => row.status === "approved").length;
  const draft = payments.filter((row) => row.status === "draft").length;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Period", value: ledger.period ?? "—" },
          { label: "Revenue", value: ledger.revenue ?? "—" },
          { label: "Expenses", value: ledger.expenses ?? "—" },
          { label: "Open invoices", value: String(invoices.length) },
        ].map((card) => (
          <div key={card.label} className="border border-border bg-inset/60 px-4 py-3">
            <Kicker>{card.label}</Kicker>
            <p className="mt-2 text-metric text-foreground">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-px overflow-hidden border border-border bg-border lg:grid-cols-3">
        <Lane
          title="Invoice lane"
          hint={`${invoices.length} records`}
          rows={invoices.slice(0, 5).map((row) => ({
            id: row.id,
            primary: row.amount,
            secondary: `${row.client_id} · ${row.description ?? "—"}`,
          }))}
        />
        <Lane
          title="Payment approval"
          hint={`${draft} draft · ${approved} approved`}
          rows={payments.slice(0, 5).map((row, i) => ({
            id: row.id ?? `P-${i}`,
            primary: row.status,
            secondary: `${row.invoice_id} · ${row.amount ?? "—"}`,
            tone: row.status === "approved" ? "ok" : row.status === "draft" ? "warn" : undefined,
          }))}
        />
        <Lane
          title="Journal / inbox"
          hint={`${journal.length} journal · ${inbox.length} inbox`}
          rows={[
            ...journal.slice(0, 2).map((row, i) => ({
              id: `J-${i}`,
              primary: row.amount,
              secondary: row.memo ?? "Journal entry",
            })),
            ...inbox.slice(0, 3).map((row) => ({
              id: row.id,
              primary: row.subject ?? "Message",
              secondary: row.from ?? row.client_id ?? "—",
            })),
          ]}
        />
      </div>
    </div>
  );
}

function Lane({
  title,
  hint,
  rows,
}: {
  title: string;
  hint: string;
  rows: { id: string; primary: string; secondary: string; tone?: "ok" | "warn" }[];
}) {
  return (
    <div className="bg-panel p-4">
      <div className="flex items-baseline justify-between gap-2">
        <Kicker>{title}</Kicker>
        <span className="text-meta">{hint}</span>
      </div>
      <ul className="mt-3 space-y-2">
        {rows.length === 0 ? (
          <li className="text-[12px] text-muted-foreground">No records in this lane.</li>
        ) : (
          rows.map((row) => (
            <li key={row.id} className="border-b border-border/80 pb-2 last:border-0">
              <p
                className={cn(
                  "font-mono text-[12px] text-foreground",
                  row.tone === "ok" && "text-success",
                  row.tone === "warn" && "text-warning",
                )}
              >
                {row.primary}
              </p>
              <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{row.secondary}</p>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

export function AccountingTables({ state }: { state: Record<string, unknown> }) {
  const invoices = recordsFromMap<Invoice>(state.invoices);
  const clients = recordsFromMap<Client>(state.clients);
  const payments = recordsFromMap<Payment>(state.payments).map((row, index) => ({
    id: row.id ?? Object.keys((state.payments as Record<string, unknown>) ?? {})[index] ?? `P-${index}`,
    ...row,
  }));
  const suppliers = recordsFromMap<Supplier>(state.suppliers);
  const journal = recordsFromMap<Journal>(state.journal).map((row, index) => ({
    id: Object.keys((state.journal as Record<string, unknown>) ?? {})[index] ?? `J-${index}`,
    ...row,
  }));
  const employees = recordsFromMap<Employee>(state.employees);
  const payroll = recordsFromMap<Payroll>(state.payroll);

  return (
    <div className="space-y-8">
      <section>
        <Kicker className="mb-3">Invoice management</Kicker>
        <DataTable tableKey="lab-invoices" columns={invoiceColumns} data={invoices} filterPlaceholder="Filter invoices…" />
      </section>
      <section>
        <Kicker className="mb-3">Payment approval</Kicker>
        <DataTable tableKey="lab-payments" columns={paymentColumns} data={payments} filterPlaceholder="Filter payments…" />
      </section>
      <section>
        <Kicker className="mb-3">Customer accounts · sensitive markers</Kicker>
        <DataTable tableKey="lab-clients" columns={clientColumns} data={clients} filterPlaceholder="Filter accounts…" />
      </section>
      <section>
        <Kicker className="mb-3">Suppliers / bank details</Kicker>
        <DataTable tableKey="lab-suppliers" columns={supplierColumns} data={suppliers} filterPlaceholder="Filter suppliers…" />
      </section>
      <section>
        <Kicker className="mb-3">Journal</Kicker>
        <DataTable tableKey="lab-journal" columns={journalColumns} data={journal} filterPlaceholder="Filter journal…" />
      </section>
      {(employees.length > 0 || payroll.length > 0) && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div>
            <Kicker className="mb-3">Employees</Kicker>
            <ul className="divide-y divide-border border border-border">
              {employees.map((row) => (
                <li key={row.id} className="flex justify-between px-3 py-2 text-[13px]">
                  <span>{row.name}</span>
                  <span className="text-meta">{row.title ?? row.id}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <Kicker className="mb-3">Payroll markers</Kicker>
            <ul className="divide-y divide-border border border-border">
              {payroll.map((row) => (
                <li key={row.id} className="flex justify-between px-3 py-2 text-[13px]">
                  <span className="font-mono text-cyan">{row.token ?? row.id}</span>
                  <span className="tabular">{row.amount ?? "—"}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}

export function AccountingPermissions({
  role,
  scopes,
  tools,
}: {
  role: string;
  scopes: Record<string, string[]>;
  tools: { name: string; roles: string[]; deny_policy: string | null }[];
}) {
  const scope = scopes[role] ?? [];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="border border-border bg-inset/50 p-4">
        <Kicker>Client scope</Kicker>
        <p className="mt-2 text-[13px] text-muted-foreground">Records this role may touch in the simulation.</p>
        <ul className="mt-3 space-y-1 font-mono text-[12px] text-foreground">
          {scope.length ? scope.map((id) => <li key={id}>{id}</li>) : <li className="text-muted-foreground">No scoped clients</li>}
        </ul>
      </div>
      <div className="border border-border bg-inset/50 p-4">
        <Kicker>Tool permissions</Kicker>
        <ul className="mt-3 max-h-56 space-y-2 overflow-auto text-[12px]">
          {tools.map((tool) => {
            const allowed = tool.roles.includes(role);
            return (
              <li key={tool.name} className="flex items-start justify-between gap-3 border-b border-border/70 pb-2">
                <span>
                  <span className="font-mono text-foreground">{tool.name}</span>
                  {!allowed && tool.deny_policy ? (
                    <span className="mt-0.5 block text-[11px] text-muted-foreground">{tool.deny_policy}</span>
                  ) : null}
                </span>
                <span className={`font-mono text-[10px] uppercase ${allowed ? "text-success" : "text-destructive"}`}>
                  {allowed ? "allow" : "deny"}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
