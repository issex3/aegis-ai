# Incident Response Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC7.3, CC7.4, CC7.5 |

## Purpose

Define how Aegis AI detects, contains, investigates, and communicates security incidents affecting the assessment platform or customer data.

## Severity

| Level | Example |
|---|---|
| Critical | Cross-tenant data exposure, credential dump, production ransomware |
| High | Confirmed account takeover of an administrator, widespread authentication outage |
| Medium | Single-tenant unauthorised access, failed backup window |
| Low | Blocked brute force with no compromise |

## Process (to be exercised)

1. **Detect** — security logs (`aegis.security`), audit events, customer reports, dependency alerts.
2. **Triage** — on-call engineer (role to be named) classifies severity within 4 hours of awareness for High/Critical.
3. **Contain** — revoke sessions, rotate `ENCRYPTION_KEY` with `ENCRYPTION_KEY_PREVIOUS`, disable affected API keys, take a system offline if required.
4. **Eradicate and recover** — patch, restore from backup only after the restoration procedure has been tested.
5. **Communicate** — affected customers notified without undue delay where personal data or credentials may have been involved. Legal timelines are a management and counsel decision.
6. **Learn** — written post-incident review. No tabletop exercise has been run.

## Evidence

Tickets, security log extracts, and the post-incident review. None are fabricated in this repository.

## Contacts

On-call roster, customer notification templates, and regulator contacts are **not** filled in. Management must complete them before this policy is approved.
