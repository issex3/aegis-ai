# Logging and Monitoring Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC7.2, CC7.3 |

## Streams

| Stream | Destination today | Protection |
|---|---|---|
| Application logs | stdout (`logging.basicConfig`) | Host/platform configuration; not append-only in the app |
| Security events | logger `aegis.security`, JSON lines | Same as stdout; must be shipped to append-only storage in production |
| Audit events | `audit_events` table, hash-chained per organisation | Readable by tenant administrators; mutable database rows, so not a WORM store |

## Events captured in code

Successful and failed authentication, lockouts, MFA enable/disable, password reset, member and role changes, credential store/rotate/destroy, licensed key create/revoke, organisation export/delete, retention changes, cross-tenant denials, HTTP 401/403/429, sandbox/assessment job limits, intelligence record approval.

## What is not logged

Passwords, tokens, ciphertext, raw credentials. Evidence redaction also strips common secret patterns.

## Retention and alerting

- Application log retention is a platform setting (proposed 365 days). Not configured here.
- Alerting to a SIEM or on-call is **not implemented**. In-app notifications exist for product events, not for SOC detection rules.
- Hash-chain verification is a function of how events are written; there is no continuous monitor that alarms on a broken chain.

Production must ship `aegis.security` to an external, access-controlled log store before Type II.
