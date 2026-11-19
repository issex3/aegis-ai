"""Extensible taxonomy: industries, threat classes, capabilities, and data classes.

To add an industry, register an IndustryDefinition here, add a sandbox definition, and add a library module
under app/scenarios/library. Nothing else in the engine needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.catalog import CATEGORIES

SCENARIO_CATEGORIES = (*CATEGORIES, "social_engineering", "output_integrity")

THREATS: dict[str, dict] = {
    "LLM01": {"name": "Prompt injection", "reference": "OWASP Top 10 for LLM Applications 2025, LLM01"},
    "LLM02": {"name": "Sensitive information disclosure", "reference": "OWASP Top 10 for LLM Applications 2025, LLM02"},
    "LLM05": {"name": "Improper output handling", "reference": "OWASP Top 10 for LLM Applications 2025, LLM05"},
    "LLM06": {"name": "Excessive agency", "reference": "OWASP Top 10 for LLM Applications 2025, LLM06"},
    "LLM07": {"name": "System prompt leakage", "reference": "OWASP Top 10 for LLM Applications 2025, LLM07"},
    "LLM09": {"name": "Misinformation", "reference": "OWASP Top 10 for LLM Applications 2025, LLM09"},
    "AEG-01": {"name": "Social engineering of the agent", "reference": "Aegis threat class. Pretexting, urgency, and false authority."},
    "AEG-02": {"name": "Authorisation boundary bypass", "reference": "Aegis threat class. Acting outside the assigned scope or role."},
    "AEG-03": {"name": "Business integrity manipulation", "reference": "Aegis threat class. Altering figures, records, or workflow state."},
    "AEG-04": {"name": "Missed mandatory control", "reference": "Aegis threat class. A required safeguard such as escalation is not performed."},
}

DATA_CLASSES: dict[str, str] = {
    "personal": "Personal data",
    "financial": "Financial records",
    "payment": "Payment and bank details",
    "health": "Health information",
    "legal_privileged": "Privileged legal material",
    "commercial": "Commercial and pricing data",
    "internal": "Internal instructions and playbooks",
}

SENSITIVITY = ("low", "moderate", "high", "critical")


@dataclass(frozen=True)
class Capability:
    key: str
    label: str
    kind: str
    keywords: tuple[str, ...]


CAPABILITIES: dict[str, Capability] = {
    item.key: item
    for item in (
        Capability("conversation.untrusted", "Receives untrusted user input", "surface", ("chat", "customer", "user", "message", "conversation", "enquir", "caller", "client")),
        Capability("instructions.confidential", "Holds confidential instructions", "surface", ("system prompt", "playbook", "internal", "instructions", "guidelines", "script")),
        Capability("content.ingest", "Reads external documents or messages", "surface", ("attachment", "upload", "inbox", "email", "document", "pdf", "file", "invoice", "receipt", "letter")),
        Capability("customer.read", "Reads customer or account records", "data", ("customer record", "customer details", "account details", "look up customer", "lookup customer", "customer data", "customer profile", "order history")),
        Capability("customer.modify", "Changes customer account details", "action", ("update account", "change email", "reset password", "modify account", "update address", "account change", "update customer")),
        Capability("refunds.issue", "Issues refunds or credits", "action", ("refund", "credit note", "compensation", "goodwill")),
        Capability("orders.read", "Reads orders and deliveries", "data", ("order", "delivery", "shipment", "tracking")),
        Capability("policy.apply", "Applies business policy", "surface", ("policy", "eligibility", "terms", "returns window", "refund window")),
        Capability("escalation.handoff", "Escalates to a human", "action", ("escalat", "hand off", "handoff", "transfer to a human", "supervisor", "complaint", "fraud report")),
        Capability("invoices.process", "Processes invoices", "data", ("invoice", "accounts payable", "bill", "receivable")),
        Capability("invoices.modify", "Changes invoice records", "action", ("update invoice", "amend invoice", "credit invoice", "edit invoice")),
        Capability("payments.initiate", "Drafts or initiates payments", "action", ("payment", "pay supplier", "transfer", "remittance", "payment run", "draft payment")),
        Capability("payments.approve", "Approves or releases payments", "action", ("approve payment", "authorise payment", "authorize payment", "release payment", "sign off payment")),
        Capability("suppliers.bank", "Manages supplier or payee bank details", "action", ("supplier", "vendor", "bank details", "payee", "sort code", "iban")),
        Capability("payroll.read", "Accesses payroll", "data", ("payroll", "salary", "salaries", "wages", "payslip")),
        Capability("finance.reporting", "Produces financial reports", "action", ("management report", "management accounts", "journal", "ledger", "board pack", "p&l", "profit and loss", "month-end", "month end")),
        Capability("finance.calculation", "Performs financial calculations", "action", ("calculat", "vat", "tax", "totals", "reconcil", "sum")),
        Capability("patients.read", "Reads patient records", "data", ("patient", "medical record", "health record", "appointment", "nhs", "clinic")),
        Capability("clinical.content", "Handles clinical or symptom content", "surface", ("symptom", "triage", "medication", "medical advice", "dosage", "clinical")),
        Capability("access.manage", "Changes access permissions", "action", ("grant access", "permission", "sharing settings", "access rights", "record access")),
        Capability("messaging.send", "Sends messages or email", "action", ("send message", "sms", "text message", "notify", "send email", "outreach", "email customers", "reply to")),
        Capability("legal.read", "Reads legal matters and documents", "data", ("contract", "case file", "matter", "legal document", "disclosure bundle", "brief", "lease")),
        Capability("legal.edit", "Drafts or edits legal documents", "action", ("draft", "redline", "amend", "edit document", "markup")),
        Capability("documents.share", "Shares documents externally", "action", ("share document", "send to client", "external party", "disclose", "share with")),
        Capability("crm.read", "Reads CRM records", "data", ("crm", "contact", "lead", "prospect", "salesforce", "hubspot", "account plan")),
        Capability("crm.write", "Updates CRM records", "action", ("update contact", "update record", "log activity", "update crm", "edit contact")),
        Capability("discounts.apply", "Applies discounts or pricing", "action", ("discount", "pricing", "quote", "promotion", "price")),
        Capability("pipeline.manage", "Manages the sales pipeline", "action", ("pipeline", "deal stage", "opportunity", "forecast", "close deals", "closed won")),
        Capability("data.export", "Exports data in bulk", "action", ("export", "download", "bulk", "csv", "extract list")),
    )
}

BASELINE_CAPABILITIES = ("conversation.untrusted", "instructions.confidential")


@dataclass(frozen=True)
class IndustryDefinition:
    slug: str
    name: str
    summary: str
    sandbox: str
    typical_capabilities: tuple[str, ...]
    typical_data: tuple[str, ...]


INDUSTRIES: dict[str, IndustryDefinition] = {}


def register_industry(definition: IndustryDefinition) -> None:
    unknown = [key for key in definition.typical_capabilities if key not in CAPABILITIES]
    if unknown:
        raise ValueError(f"Unknown capabilities for {definition.slug}: {unknown}")
    INDUSTRIES[definition.slug] = definition


for _definition in (
    IndustryDefinition(
        "customer_service",
        "Customer service",
        "Support agents that answer customers, read accounts, issue refunds, and escalate.",
        "customer_service",
        ("conversation.untrusted", "customer.read", "refunds.issue", "orders.read", "policy.apply", "escalation.handoff", "content.ingest"),
        ("personal", "payment", "internal"),
    ),
    IndustryDefinition(
        "accounting",
        "Accounting and finance",
        "Bookkeeping, accounts payable, payroll, and reporting agents.",
        "accounting",
        ("invoices.process", "payments.initiate", "suppliers.bank", "finance.reporting", "finance.calculation", "content.ingest"),
        ("financial", "payment", "personal"),
    ),
    IndustryDefinition(
        "healthcare",
        "Healthcare",
        "Patient-facing and administrative agents in clinical settings.",
        "healthcare",
        ("conversation.untrusted", "patients.read", "clinical.content", "messaging.send"),
        ("health", "personal"),
    ),
    IndustryDefinition(
        "legal",
        "Legal",
        "Matter, document, and client-intake agents in law firms.",
        "legal",
        ("legal.read", "legal.edit", "content.ingest", "documents.share"),
        ("legal_privileged", "personal"),
    ),
    IndustryDefinition(
        "sales_crm",
        "Sales and CRM",
        "Sales assistants that work CRM records, pricing, pipeline, and email.",
        "sales_crm",
        ("crm.read", "crm.write", "discounts.apply", "pipeline.manage", "messaging.send", "content.ingest"),
        ("commercial", "personal"),
    ),
):
    register_industry(_definition)
