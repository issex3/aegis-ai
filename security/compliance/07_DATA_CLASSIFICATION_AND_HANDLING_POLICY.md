# Data Classification and Handling Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC6.1, P1.1 (if privacy in scope later) |

## Classes

| Class | Examples | Handling |
|---|---|---|
| Restricted | Agent API credentials, MFA secrets, session tokens, encryption keys, Stripe secrets | Encrypted at rest (Fernet, tenant-derived keys for agent credentials); never in API responses or ordinary logs |
| Confidential | Assessment evidence, findings, reports, organisation membership, audit events | Tenant-scoped queries; administrators for audit trail; TLS in transit in production |
| Internal | Scenario library, sandbox definitions, catalogue | Public to authenticated users of any tenant |
| Public | Marketing site copy, published legal pages | No authentication |

## Handling rules

- Do not copy Restricted data into tickets or chat without redaction.
- Evidence is passed through secret redaction before storage. Redaction is heuristic; it cannot guarantee that an agent did not echo a novel secret.
- Default testing uses synthetic sandbox records, not customer production data.
- Intelligence contribution requires explicit organisation consent and omits raw customer replies.

## Media and paper

Aegis is a software service. Paper handling and removable media are organisational procedures and are not implemented in the product.
