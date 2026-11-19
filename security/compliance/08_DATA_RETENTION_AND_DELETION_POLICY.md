# Data Retention and Deletion Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC6.5 |

## Default periods

| Record | Default | Configurable |
|---|---|---|
| Organisation operational data (agents, assessments, evidence, reports) | 365 days (`organisations.retention_days`, range 30–2555) | Owner/admin via `/settings/retention` |
| Sessions | Absolute 12 hours, idle 8 hours, then ineligible | Environment settings |
| Password reset tokens | 30 minutes | No |
| MFA challenges | 5 minutes | No |
| Invitations | 7 days | No |
| Audit events | Retained after tenant deletion (actor anonymised where the user has no remaining membership) | Not customer-configurable |
| Backups | Proposed 30 days PITR | Infrastructure, not in application |

A scheduled job that purges assessments older than `retention_days` is **not implemented**. The period is stored so that a future job and Type II operating effectiveness have a defined rule. Until that job exists, retention is a policy statement plus owner-initiated deletion, not automatic enforcement.

## Customer export and deletion

- `GET /api/v1/organisations/export` — JSON without credential secrets, session tokens, or MFA material. Audited.
- `POST /api/v1/organisations/delete` — owner only. Destroys credential ciphertext, deletes tenant operational rows, anonymises users who have no other membership, retains audit events. Irreversible.

## Secure deletion of credentials

On rotation, origin change, explicit delete, or tenant delete, ciphertext is overwritten with a non-reversible placeholder before the row is removed or retained for linkage.
