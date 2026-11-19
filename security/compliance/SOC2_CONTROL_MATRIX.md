# SOC 2 Control Matrix (Security TSC, path to Type I then Type II)

| | |
|---|---|
| Document status | DRAFT — internal mapping, not an auditor opinion |
| Date | 3 November 2026 |
| Framework | AICPA Trust Services Criteria 2017 (2022 points of focus), Security category primarily |
| Company status | **Not SOC 2 certified.** Not SOC 2 compliant as a claim. |

Statuses used:

- Implemented and verified — present in code and covered by automated tests in this repository.
- Implemented but not independently verified — present in code or scripts; no independent review or operating-period evidence.
- Partially implemented — real control exists but gaps remain.
- Not implemented — absent or only a policy draft.
- Not applicable — with justification.

Evidence collection methods are the intended method. **No fake evidence is attached.**

---

## Control environment and people

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-CE-01 | CC1.1, CC1.2 | Security policies exist and are approved | 15 draft policies in `security/compliance/` | Signed policy set, version history | Management approval record | Management | Partially implemented | Approve, assign owners, publish internally |
| CTRL-CE-02 | CC1.3, CC1.4 | Personnel are suitable and trained | No HR or LMS integration | Background check policy (if used), training completions | HR files | Management | Not implemented | Hire/HR process, annual training |
| CTRL-CE-03 | CC2.2, CC2.3 | Responsibilities and incidents can be communicated | Policies name roles as functions, not people; no on-call roster | Org chart, on-call, customer notification path | Management pack | Management | Not implemented | Name roles, comms templates |

## Risk assessment

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-RA-01 | CC3.1, CC3.2 | Risks are identified and treated | `SOC2_GAP_ASSESSMENT.md` from a code inspection | Annual risk register signed by management | Risk review meeting | Engineering + management | Partially implemented | Management workshop; residual risk acceptance |
| CTRL-RA-02 | CC3.3, CC3.4 | Fraud and change in environment are considered | Insider credential-redirection (SEC-001) mitigated in code; no fraud risk workshop | Workshop notes | Meeting minutes | Management | Partially implemented | Formal fraud discussion |
| CTRL-RA-03 | CC9.2 | Vendor risk is managed | Policy draft; Stripe and customer endpoints documented | Vendor inventory, SOC reports | Annual vendor review | Management | Not implemented | Complete vendor reviews |

## Logical access

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-AC-01 | CC6.1 | Unique IDs and strong authentication | Email unique; Argon2id; hashed sessions; MFA TOTP | Auth tests in `test_stage1.py`, `test_security.py` | pytest | Engineering | Implemented but not independently verified | Independent pen test of auth |
| CTRL-AC-02 | CC6.1, CC6.3 | MFA for administrators | TOTP + recovery codes; production start requires `MFA_REQUIRED_FOR_ADMINS=true` | MFA tests; production config | pytest; production config review | Engineering | Implemented but not independently verified | Enforce in the deployed environment |
| CTRL-AC-03 | CC6.1, CC6.2 | RBAC and least privilege | Server-side `require_role`; credential and origin changes are admin; secret-on-create is admin | Privilege tests | pytest | Engineering | Implemented but not independently verified | Access reviews of members |
| CTRL-AC-04 | CC6.1 | Brute-force protection | Per-IP and per-account rate limits; account lockout | Lockout test | pytest | Engineering | Implemented but not independently verified | Shared limiter is in-process; use Redis in multi-instance production |
| CTRL-AC-05 | CC6.1 | Session management | TTL, idle timeout, logout revocation, revoke others on password change/reset, list/revoke sessions | Auth tests | pytest | Engineering | Implemented but not independently verified | — |
| CTRL-AC-06 | CC6.1 | Password reset | Hashed 30-minute tokens; uniform forgot-password response | Reset test | pytest | Engineering | Implemented but not independently verified | Configure SMTP in production |
| CTRL-AC-07 | CC6.1 | Tenant isolation | Session-bound `organisation_id`; scoped queries; cross-tenant probes audited | Isolation tests | pytest | Engineering | Implemented but not independently verified | Independent IDOR test |
| CTRL-AC-08 | CC6.2 | Joiner/mover/leaver for customers | Invites, role change, last-owner protection, session revoke on removal | Member tests | pytest | Engineering | Implemented but not independently verified | Staff joiner/leaver process |
| CTRL-AC-09 | CC6.2 | Privileged platform access | `is_platform_operator` flag; approvals audited | Code + audit action `intelligence_record_approved` | Code review | Engineering | Partially implemented | Break-glass procedure, MFA on the operator account in production |
| CTRL-AC-10 | CC6.3 | Quarterly access reviews | Not implemented | Review spreadsheet signed | Calendar reminder | Management | Not implemented | Run reviews |
| CTRL-AC-11 | CC6.6 | Encryption in transit | Production validation requires HTTPS public URL and secure cookies; local Compose has no TLS | Production config | Config review | Engineering / cloud | Partially implemented | Terminate TLS on the host |
| CTRL-AC-12 | CC6.1, CC6.7 | Encryption at rest of secrets | Tenant-derived Fernet; MFA secrets bound to user id | Credential tests | pytest | Engineering | Implemented but not independently verified | KMS for the master key |
| CTRL-AC-13 | CC6.1 | Licensed API keys lifecycle | Hashed keys, expiry, list, revoke, audit | Licensed key tests | pytest | Engineering | Implemented but not independently verified | — |

## System operations and monitoring

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-OP-01 | CC7.2 | Security logging | `aegis.security` JSON logger + hash-chained `audit_events` | Log samples, audit query | Log export | Engineering | Partially implemented | Ship to append-only store; restrict DB mutation |
| CTRL-OP-02 | CC7.2, CC7.3 | Detection and alerting | 401/403/429 and cross-tenant events logged; no SIEM rules | Alert tickets | SIEM | Engineering | Not implemented | Detection rules, on-call |
| CTRL-OP-03 | CC7.1 | Vulnerability scanning | CI: pip-audit, npm audit, bandit, secret scan | CI logs | GitHub Actions once hosted | Engineering | Implemented but not independently verified | Host the repo; fix remaining transitive CVEs if pip-audit reports any after deploy |
| CTRL-OP-04 | CC7.3, CC7.4, CC7.5 | Incident response | Policy draft only | Ticket + PIR | IR process | Management | Not implemented | Tabletop exercise |
| CTRL-OP-05 | CC7.1 | Secure configuration | Production start-up validation; security headers; request size limit; CORS allow-list | Header tests; config module | pytest | Engineering | Implemented but not independently verified | Harden live host |
| CTRL-OP-06 | CC7.1 | Execution isolation | App-level SSRF, concurrency, timeouts; in-process sandbox | SSRF and PDF tests; architecture note | pytest + `EXECUTION_ISOLATION_ARCHITECTURE.md` | Engineering | Partially implemented | Dedicated worker network; MicroVMs only if customer code is introduced |
| CTRL-OP-07 | CC7.2 | Evidence handling | Secret redaction before storage | Redaction unit use in runner/execution | pytest (credential secrecy, export) | Engineering | Implemented but not independently verified | Heuristic redaction cannot be complete |

## Change management

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-CH-01 | CC8.1 | Changes are reviewed and tested | pytest + CI workflow file | PR reviews, CI green | Git host | Engineering | Partially implemented | Initialise hosted git, protect `main`, require reviews |
| CTRL-CH-02 | CC8.1 | Separated environments | Dev / test / production settings | Environment list | Config | Engineering | Partially implemented | Provision a real production account |
| CTRL-CH-03 | CC8.1 | Database changes are migrated | Alembic 0001–0007 with downgrade on 0007 | Migration files | Repo | Engineering | Implemented but not independently verified | Never run destructive migrate without backup |

## Availability / backups

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-AV-01 | A1.2 | Backups exist and restore | Scripts only; restore untested | Restore test record | Quarterly restore | Engineering / cloud | Not implemented | Managed PostgreSQL PITR + tested restore |
| CTRL-AV-02 | A1.1, A1.3 | Capacity and recovery objectives | Concurrency limits in code; RTO/RPO proposed on paper | Metrics, DR exercise | Monitoring | Management | Partially implemented | Observability stack, DR test |

## Privacy / data lifecycle (supporting Security)

| Control ID | TSC | Objective | Implementation | Evidence required | Collection method | Responsible role | Status | Outstanding work |
|---|---|---|---|---|---|---|---|---|
| CTRL-DL-01 | CC6.5 | Export and deletion | Owner export (no secrets) and irreversible delete | Deletion test | pytest | Engineering | Implemented but not independently verified | Document customer request SLA |
| CTRL-DL-02 | CC6.5 | Retention enforcement | Configurable `retention_days`; no scheduled purge job | Job logs | Scheduler | Engineering | Partially implemented | Implement and operate the purge job |

---

## Evidence collection framework

| Evidence type | Cadence | Owner | System of record | Status |
|---|---|---|---|---|
| Access reviews (staff and platform operators) | Quarterly | Management | Spreadsheet / IdP | Not started |
| Access reviews (customer tenants) | Customer-driven; Aegis may remind owners | Customer owner | Product members list | Tooling present; no Aegis-operated review |
| Vulnerability scans | Every CI run + monthly manual | Engineering | CI + pip-audit/npm | CI file present; not running until git host exists |
| Security monitoring | Continuous | Engineering | SIEM (not selected) | Not implemented |
| Change approvals | Per pull request | Engineering | Git host | Not implemented (no hosted repo) |
| Backup testing | Quarterly | Engineering | Restore ticket | Not implemented |
| Incident response exercises | Annual tabletop | Management | PIR notes | Not implemented |
| Employee security training | At hire + annual | Management | LMS | Not implemented |
| Vendor reviews | Annual | Management | Vendor folder | Not implemented |
| Penetration testing | Before Type I, then annual | Management | Report from independent tester | Not implemented |
| Risk assessments | Annual | Management | Risk register | Draft technical assessment only |

Independent auditor assessment is required for every “implemented” control before any SOC 2 report can be issued. This matrix is not that assessment.
