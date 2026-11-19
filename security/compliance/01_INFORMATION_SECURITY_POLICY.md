# Information Security Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Owner | To be designated (proposed: Head of Engineering) |
| Applies to | Aegis AI personnel, contractors, and systems that process customer assessment data |
| Related criteria | CC1.2, CC2.1, CC5.1, CC6.1 |

Aegis AI provides automated security testing of customer AI agents. This policy states how the company intends to protect the confidentiality, integrity, and availability of that service. It is not a SOC 2 report and it does not assert that an examination has occurred.

## Objectives

1. Protect customer organisation data, agent configuration, encrypted credentials, assessment evidence, and reports from unauthorised access.
2. Treat customer agents, prompts, and responses as untrusted input.
3. Prefer synthetic test data; do not require production customer records in the default testing path.
4. Record security-relevant events and review them.
5. Correct weaknesses according to the Vulnerability Management Policy.

## Scope

This policy covers the Aegis web application, API, worker, databases, and the development process documented in this repository. Cloud accounts, identity providers, and office IT are in scope once management names the systems in use. They are not described here as implemented.

## Roles

| Role | Responsibility |
|---|---|
| Organisation owner (customer) | Administers the customer tenant, including members, MFA for administrators in production, export, and deletion |
| Platform operator | Reviews contributed intelligence records; provisioned only by an explicit database flag |
| Engineering | Builds and maintains controls in this repository |
| Management (unnamed) | Approves this policy, residual risk, and exceptions |

No named employees, completed training, or prior audits are recorded in this document.

## Principles

- Least privilege on the server. Browser checks are not authorisation.
- Tenant isolation by organisation membership bound to the server-side session.
- Secrets encrypted at rest; never returned in API responses.
- Changes follow the Change Management Policy.

## Exceptions

Exceptions require written management approval and an expiry date. None are recorded.

## Review

Review at least annually, and after a material incident or architecture change.
