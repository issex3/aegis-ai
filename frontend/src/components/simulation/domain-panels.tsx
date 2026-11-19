"use client";

import { DataTable, researchTableFeatures } from "@/components/data/data-table";
import { Kicker } from "@/components/layout";
import type { LabEnvironmentKey } from "@/lib/simulation";
import { recordsFromMap } from "@/lib/simulation";
import type { ColumnDef } from "@tanstack/react-table";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Col<T extends Record<string, any>> = Array<ColumnDef<typeof researchTableFeatures, T>>;

function RecordSection<T extends Record<string, unknown>>({
  title,
  columns,
  data,
  placeholder,
  tableKey,
}: {
  title: string;
  columns: Col<T>;
  data: T[];
  placeholder: string;
  tableKey: string;
}) {
  return (
    <section>
      <Kicker className="mb-3">{title}</Kicker>
      {data.length === 0 ? (
        <p className="border border-dashed border-border px-4 py-6 text-[13px] text-muted-foreground">No records yet — tools may populate this collection.</p>
      ) : (
        <DataTable tableKey={tableKey} columns={columns} data={data} filterPlaceholder={placeholder} />
      )}
    </section>
  );
}

function OverviewStrip({ items }: { items: { label: string; value: string }[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="border border-border bg-inset/60 px-4 py-3">
          <Kicker>{item.label}</Kicker>
          <p className="mt-2 text-metric text-foreground">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

export function DomainOverview({ labKey, state }: { labKey: LabEnvironmentKey; state: Record<string, unknown> }) {
  switch (labKey) {
    case "healthcare": {
      const patients = recordsFromMap(state.patients);
      const appointments = recordsFromMap(state.appointments);
      const notes = recordsFromMap(state.clinical_notes);
      const outbox = recordsFromMap(state.outbox);
      return (
        <OverviewStrip
          items={[
            { label: "Patients", value: String(patients.length) },
            { label: "Appointments", value: String(appointments.length) },
            { label: "Clinical notes", value: String(notes.length) },
            { label: "Outbox", value: String(outbox.length) },
          ]}
        />
      );
    }
    case "legal": {
      const cases = recordsFromMap(state.cases);
      const documents = recordsFromMap(state.documents);
      const clients = recordsFromMap(state.clients);
      return (
        <OverviewStrip
          items={[
            { label: "Matters", value: String(cases.length) },
            { label: "Documents", value: String(documents.length) },
            { label: "Clients", value: String(clients.length) },
            { label: "Firms", value: String(recordsFromMap(state.firms).length) },
          ]}
        />
      );
    }
    case "retail": {
      const orders = recordsFromMap(state.orders);
      const products = recordsFromMap(state.products);
      const refunds = recordsFromMap(state.refunds);
      return (
        <OverviewStrip
          items={[
            { label: "Orders", value: String(orders.length) },
            { label: "Products", value: String(products.length) },
            { label: "Customers", value: String(recordsFromMap(state.customers).length) },
            { label: "Refunds", value: String(refunds.length) },
          ]}
        />
      );
    }
    case "customer_service": {
      return (
        <OverviewStrip
          items={[
            { label: "Customers", value: String(recordsFromMap(state.customers).length) },
            { label: "Orders", value: String(recordsFromMap(state.orders).length) },
            { label: "Policies", value: String(recordsFromMap(state.policies).length) },
            { label: "Escalations", value: String(recordsFromMap(state.escalations).length) },
          ]}
        />
      );
    }
    case "sales_crm": {
      return (
        <OverviewStrip
          items={[
            { label: "Accounts", value: String(recordsFromMap(state.accounts).length) },
            { label: "Contacts", value: String(recordsFromMap(state.contacts).length) },
            { label: "Deals", value: String(recordsFromMap(state.deals).length) },
            { label: "Outbox", value: String(recordsFromMap(state.outbox).length) },
          ]}
        />
      );
    }
    default:
      return null;
  }
}

export function DomainTables({ labKey, state }: { labKey: LabEnvironmentKey; state: Record<string, unknown> }) {
  switch (labKey) {
    case "healthcare":
      return <HealthcareTables state={state} />;
    case "legal":
      return <LegalTables state={state} />;
    case "retail":
      return <RetailTables state={state} />;
    case "customer_service":
      return <CustomerServiceTables state={state} />;
    case "sales_crm":
      return <SalesCrmTables state={state} />;
    default:
      return null;
  }
}

function HealthcareTables({ state }: { state: Record<string, unknown> }) {
  type Patient = { id: string; name: string; phone_on_file?: string; reference?: string };
  type Appt = { id: string; patient_id: string; time?: string; clinic?: string };
  type Note = { patient_id: string; note?: string };
  const patients = recordsFromMap<Patient>(state.patients);
  const appointments = recordsFromMap<Appt>(state.appointments);
  const notes = recordsFromMap<Note>(state.clinical_notes).map((row, i) => ({
    id: row.patient_id ?? `N-${i}`,
    ...row,
  }));
  const protocols = state.protocols && typeof state.protocols === "object" ? Object.entries(state.protocols as Record<string, string>) : [];

  const patientCols: Col<Patient> = [
    { accessorKey: "id", header: "Patient", enableSorting: true },
    { accessorKey: "name", header: "Name", enableSorting: true },
    { accessorKey: "phone_on_file", header: "Phone" },
    {
      accessorKey: "reference",
      header: "Reference",
      cell: (info) => <span className="font-mono text-[11px] text-cyan">{String(info.getValue() ?? "—")}</span>,
    },
  ];
  const apptCols: Col<Appt> = [
    { accessorKey: "id", header: "Appointment", enableSorting: true },
    { accessorKey: "patient_id", header: "Patient", enableSorting: true },
    { accessorKey: "time", header: "Time" },
    { accessorKey: "clinic", header: "Clinic" },
  ];
  const noteCols: Col<Note & { id: string }> = [
    { accessorKey: "patient_id", header: "Patient", enableSorting: true },
    {
      accessorKey: "note",
      header: "Clinical note",
      cell: (info) => <span className="line-clamp-2 text-muted-foreground">{String(info.getValue() ?? "")}</span>,
    },
  ];

  return (
    <div className="space-y-8">
      <RecordSection title="Patients" tableKey="lab-patients" columns={patientCols} data={patients} placeholder="Filter patients…" />
      <RecordSection title="Appointments" tableKey="lab-appointments" columns={apptCols} data={appointments} placeholder="Filter appointments…" />
      <RecordSection title="Clinical notes" tableKey="lab-notes" columns={noteCols} data={notes} placeholder="Filter notes…" />
      {protocols.length ? (
        <section>
          <Kicker className="mb-3">Protocols</Kicker>
          <ul className="divide-y divide-border border border-border">
            {protocols.map(([topic, body]) => (
              <li key={topic} className="px-3 py-2 text-[13px]">
                <span className="font-mono text-[11px] text-faint">{topic}</span>
                <p className="mt-1 text-muted-foreground">{body}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function LegalTables({ state }: { state: Record<string, unknown> }) {
  type Case = { id: string; client_id: string; title?: string; note_token?: string };
  type Doc = { id: string; case_id: string; title?: string; status?: string; permissions?: string; body?: string };
  type Client = { id: string; name: string; token?: string };
  const cases = recordsFromMap<Case>(state.cases);
  const documents = recordsFromMap<Doc>(state.documents);
  const clients = recordsFromMap<Client>(state.clients);

  return (
    <div className="space-y-8">
      <RecordSection
        title="Matters"
        tableKey="lab-cases"
        data={cases}
        placeholder="Filter matters…"
        columns={[
          { accessorKey: "id", header: "Case", enableSorting: true },
          { accessorKey: "title", header: "Title", enableSorting: true },
          { accessorKey: "client_id", header: "Client" },
          {
            accessorKey: "note_token",
            header: "Privilege marker",
            cell: (info) => <span className="font-mono text-[11px] text-cyan">{String(info.getValue() ?? "—")}</span>,
          },
        ]}
      />
      <RecordSection
        title="Documents"
        tableKey="lab-docs"
        data={documents}
        placeholder="Filter documents…"
        columns={[
          { accessorKey: "id", header: "Document", enableSorting: true },
          { accessorKey: "title", header: "Title" },
          { accessorKey: "case_id", header: "Case" },
          { accessorKey: "status", header: "Status" },
          { accessorKey: "permissions", header: "Permissions" },
        ]}
      />
      <RecordSection
        title="Clients"
        tableKey="lab-legal-clients"
        data={clients}
        placeholder="Filter clients…"
        columns={[
          { accessorKey: "id", header: "Client", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          {
            accessorKey: "token",
            header: "Token",
            cell: (info) => <span className="font-mono text-[11px] text-cyan">{String(info.getValue() ?? "—")}</span>,
          },
        ]}
      />
    </div>
  );
}

function RetailTables({ state }: { state: Record<string, unknown> }) {
  type Order = { id: string; customer_id: string; sku?: string; status?: string; delivery?: string };
  type Product = { sku: string; name?: string };
  type Inventory = { sku: string; on_hand?: number | string };
  type Customer = { id: string; name: string; token?: string };
  const orders = recordsFromMap<Order>(state.orders);
  const products = recordsFromMap<Product>(state.products);
  const inventory = recordsFromMap<Inventory>(state.inventory);
  const customers = recordsFromMap<Customer>(state.customers);
  const refunds = recordsFromMap<{ order_id?: string; status?: string }>(state.refunds);

  return (
    <div className="space-y-8">
      <RecordSection
        title="Orders"
        tableKey="lab-orders"
        data={orders}
        placeholder="Filter orders…"
        columns={[
          { accessorKey: "id", header: "Order", enableSorting: true },
          { accessorKey: "customer_id", header: "Customer" },
          { accessorKey: "sku", header: "SKU" },
          { accessorKey: "status", header: "Status" },
          { accessorKey: "delivery", header: "Delivery" },
        ]}
      />
      <RecordSection
        title="Products / inventory"
        tableKey="lab-products"
        data={products.map((p) => ({
          ...p,
          on_hand: inventory.find((i) => i.sku === p.sku)?.on_hand ?? "—",
        }))}
        placeholder="Filter products…"
        columns={[
          { accessorKey: "sku", header: "SKU", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          { accessorKey: "on_hand", header: "On hand" },
        ]}
      />
      <RecordSection
        title="Customers"
        tableKey="lab-retail-customers"
        data={customers}
        placeholder="Filter customers…"
        columns={[
          { accessorKey: "id", header: "Customer", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          {
            accessorKey: "token",
            header: "Token",
            cell: (info) => <span className="font-mono text-[11px] text-cyan">{String(info.getValue() ?? "—")}</span>,
          },
        ]}
      />
      {refunds.length ? (
        <section>
          <Kicker className="mb-3">Refunds</Kicker>
          <ul className="divide-y divide-border border border-border">
            {refunds.map((row, i) => (
              <li key={i} className="flex justify-between px-3 py-2 text-[13px]">
                <span>{row.order_id ?? `refund-${i}`}</span>
                <span className="font-mono text-[11px] uppercase text-signal">{row.status ?? "—"}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function CustomerServiceTables({ state }: { state: Record<string, unknown> }) {
  type Customer = { id: string; name: string; email?: string; verification_phrase?: string };
  type Order = { id: string; customer_id: string; total?: string; delivered_days_ago?: number; address?: string };
  type Policy = { id: string; title?: string; body?: string };
  const customers = recordsFromMap<Customer>(state.customers);
  const orders = recordsFromMap<Order>(state.orders);
  const policies = recordsFromMap<Policy>(state.policies);
  const attachments = recordsFromMap<{ id: string; customer_id?: string; filename?: string; text?: string }>(state.attachments);

  return (
    <div className="space-y-8">
      <RecordSection
        title="Customers"
        tableKey="lab-cs-customers"
        data={customers}
        placeholder="Filter customers…"
        columns={[
          { accessorKey: "id", header: "Customer", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          { accessorKey: "email", header: "Email" },
          {
            accessorKey: "verification_phrase",
            header: "Verification",
            cell: (info) => <span className="font-mono text-[11px] text-warning">{String(info.getValue() ?? "—")}</span>,
          },
        ]}
      />
      <RecordSection
        title="Orders"
        tableKey="lab-cs-orders"
        data={orders}
        placeholder="Filter orders…"
        columns={[
          { accessorKey: "id", header: "Order", enableSorting: true },
          { accessorKey: "customer_id", header: "Customer" },
          { accessorKey: "total", header: "Total" },
          { accessorKey: "delivered_days_ago", header: "Delivered days ago" },
        ]}
      />
      <RecordSection
        title="Policies"
        tableKey="lab-policies"
        data={policies}
        placeholder="Filter policies…"
        columns={[
          { accessorKey: "id", header: "Policy", enableSorting: true },
          { accessorKey: "title", header: "Title" },
          {
            accessorKey: "body",
            header: "Body",
            cell: (info) => <span className="line-clamp-2 text-muted-foreground">{String(info.getValue() ?? "")}</span>,
          },
        ]}
      />
      {attachments.length ? (
        <section>
          <Kicker className="mb-3">Attachments</Kicker>
          <ul className="divide-y divide-border border border-border">
            {attachments.map((row) => (
              <li key={row.id} className="px-3 py-2 text-[13px]">
                <span className="font-mono text-[11px] text-faint">{row.filename ?? row.id}</span>
                <p className="mt-1 text-muted-foreground">{row.text ?? "—"}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function SalesCrmTables({ state }: { state: Record<string, unknown> }) {
  type Account = { id: string; name: string; owner?: string; notes?: string };
  type Contact = { id: string; account_id: string; name?: string; email?: string };
  type Deal = { id: string; account_id: string; stage?: string; value?: string; discount_percent?: number };
  const accounts = recordsFromMap<Account>(state.accounts);
  const contacts = recordsFromMap<Contact>(state.contacts);
  const deals = recordsFromMap<Deal>(state.deals);
  const inbox = recordsFromMap<{ id: string; account_id?: string; from?: string; body?: string }>(state.inbox);

  return (
    <div className="space-y-8">
      <RecordSection
        title="Accounts"
        tableKey="lab-accounts"
        data={accounts}
        placeholder="Filter accounts…"
        columns={[
          { accessorKey: "id", header: "Account", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          { accessorKey: "owner", header: "Owner" },
          {
            accessorKey: "notes",
            header: "Notes",
            cell: (info) => <span className="line-clamp-2 text-muted-foreground">{String(info.getValue() ?? "")}</span>,
          },
        ]}
      />
      <RecordSection
        title="Contacts"
        tableKey="lab-contacts"
        data={contacts}
        placeholder="Filter contacts…"
        columns={[
          { accessorKey: "id", header: "Contact", enableSorting: true },
          { accessorKey: "name", header: "Name" },
          { accessorKey: "account_id", header: "Account" },
          { accessorKey: "email", header: "Email" },
        ]}
      />
      <RecordSection
        title="Deals"
        tableKey="lab-deals"
        data={deals}
        placeholder="Filter deals…"
        columns={[
          { accessorKey: "id", header: "Deal", enableSorting: true },
          { accessorKey: "account_id", header: "Account" },
          { accessorKey: "stage", header: "Stage" },
          { accessorKey: "value", header: "Value" },
          { accessorKey: "discount_percent", header: "Discount %" },
        ]}
      />
      {inbox.length ? (
        <section>
          <Kicker className="mb-3">Inbox</Kicker>
          <ul className="divide-y divide-border border border-border">
            {inbox.map((row) => (
              <li key={row.id} className="px-3 py-2 text-[13px]">
                <span className="text-foreground">{row.from ?? row.id}</span>
                <p className="mt-1 text-muted-foreground">{row.body ?? "—"}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
