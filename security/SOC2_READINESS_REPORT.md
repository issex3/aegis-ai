# Aegis AI — SOC 2 Readiness Report

| | |
|---|---|
| Document status | DRAFT — internal engineering report |
| Date | 3 November 2026 |
| Scope | Aegis AI assessment platform as implemented in this repository |
| Trust services | Security (primary). Availability as a later expansion. Confidentiality/Privacy/Processing Integrity not in the current examination plan. |

**Aegis AI is not SOC 2 certified and is not claiming SOC 2 compliance.** This report describes readiness work: what was found, what was implemented in code, what still depends on infrastructure or management, and a path toward a Type I examination and later Type II.

---

## 1. How this programme was run

1. Inspected the running architecture (FastAPI, Next.js, SQLAlchemy/Alembic, Celery, Compose) and wrote `security/SOC2_GAP_ASSESSMENT.md` from verified code, not from UI labels.
2. Implemented the highest-severity engineering controls that could be real in this codebase (see section 3).
3. Added automated tests in `backend/tests/test_security.py` and extended existing suites. Full backend pytest: **65 passed** on 3 November 2026 in this environment.
4. Added CI workflow `.github/workflows/security.yml` (does not run until the project is on a git host).
5. Drafted policies, this report, the control matrix, execution-isolation architecture, and backup notes. Procedures that need management approval are marked DRAFT. No employees, training completions, tabletop exercises, or restore tests were invented.

---

## 2. Distinction of control states

### Controls actually implemented in this repository (engineering)

Covered by automated tests unless noted:

- Argon2id passwords, hashed revocable sessions, idle and absolute expiry, logout, password change that revokes other sessions.
- TOTP MFA, hashed recovery codes, MFA login challenge, production flag to require MFA for administrative actions.
- Password reset tokens (hashed, 30 minutes, single use). SMTP delivery is an operations task.
- Server-side RBAC; admin-only credentials, origin changes, audit log, members; owner-only deletion and licensed keys.
- Member invite / role change / last-owner protection; privilege-escalation tests.
- Tenant-scoped queries; cross-tenant access returns 404 and is audited when the object exists in another organisation.
- Tenant-derived Fernet keys for agent credentials; credentials never returned; destroyed on rotation, origin change, and tenant delete.
- SSRF controls without process-wide DNS patching; IP pinning; metadata and private ranges blocked.
- ReportLab dynamic text escaped (PDF markup SSRF closed in application code).
- Evidence secret redaction; organisation export without secrets; owner-initiated tenant deletion.
- Security headers, request size limit, generic errors, docs disabled in production, production start-up validation.
- Auth rate limiting (in-process) and account lockout.
- Licensed API key list/revoke/expiry.
- Assessment concurrency limits.
- Hash-chained audit events and a separate `aegis.security` JSON logger.
- Compose: loopback-only DB/Redis ports, env-based passwords, Redis requirepass, non-root images, no-new-privileges.
- Alembic migration `20261107_0007` for the new identity and audit columns.

These are **implemented but not independently verified**. Passing pytest is not a penetration test and not an auditor test of design.

### Controls implemented but not independently verified

Everything in the list above, plus:

- Dependency upgrades (`cryptography 46.0.3`, `fastapi 0.121.0`, `starlette 0.49.3`, `pytest 8.4.2`, `pyotp 2.9.0`). `pip-audit` should be re-run in CI on a hosted runner.
- Secret scanner script (one allowlisted test fixture).
- Backup and restore **scripts** (untested against production data).

### Controls requiring external infrastructure

| Need | Why the app cannot finish it |
|---|---|
| Hosted git, branch protection, required reviews | The tree was not a hosted repository with protected branches at assessment time |
| TLS termination, WAF, private networking | Not in Compose; production must sit behind HTTPS |
| Managed PostgreSQL with encryption and PITR | Volume in Compose is not a backup system |
| Redis (or equivalent) shared rate limiter | In-process limiter does not hold across multiple API replicas |
| KMS / secrets manager for `ENCRYPTION_KEY` | Still an environment variable |
| SIEM / append-only log store | Logs go to stdout |
| SMTP provider | Reset and invite email |
| Dedicated execution VPC, IMDS off, egress proxy | See `security/EXECUTION_ISOLATION_ARCHITECTURE.md` |
| MicroVMs | Not required for current functionality (no customer code execution); mandatory if that feature is added |
| Identity provider / SCIM for staff | Staff access is not in the product |

### Controls requiring company management action

- Approve the 15 DRAFT policies and name policy owners.
- Risk acceptance workshop and residual-risk sign-off.
- Staff hiring, background checks (if used), security training, and leavers.
- Vendor reviews (Stripe, host, email, future KMS/SIEM).
- Commission independent penetration testing.
- Quarterly access reviews and a tabletop incident exercise.
- Quarterly backup restore test with a written result.
- Select a SOC 2 auditor and define the system description (Type I).
- Operate the production configuration (`ENVIRONMENT=production`, `COOKIE_SECURE=true`, `MFA_REQUIRED_FOR_ADMINS=true`, PostgreSQL, HTTPS).

### Controls requiring independent auditor assessment

Every control that will appear in a Type I or Type II report. Internal pytest and this document are not substitutes.

---

## 3. Implemented security improvements (this engineering pass)

Mapped to gap-assessment IDs:

| ID | Change |
|---|---|
| SEC-004 | Escape all dynamic ReportLab text; regression test forbids network on hostile markup |
| SEC-001 | Origin change requires administrator and destroys the stored credential |
| SEC-003 | Outbound client pins resolved public IPs, uses TLS SNI, streams with a cap, does not patch `getaddrinfo` globally |
| SEC-002 | Rate limit per client IP (including `X-Forwarded-For` from trusted proxies) and per account; lockout |
| SEC-005 | TOTP MFA and production-mandatory flag for administrators |
| SEC-006 | Password reset flow |
| SEC-007 | Idle timeout, last-seen, session list/revoke, revoke others on password change |
| SEC-008 / SEC-022 | Hash-chained audit, admin-only audit API, security logger, 401/403/429 and cross-tenant events |
| SEC-009 / SEC-010 / SEC-012 | Headers, body limit, production start-up checks |
| SEC-011 | Tenant-derived keys (`v2:` ciphertext) and previous-key hook |
| SEC-013 | Compose and Dockerfile hardening (still a laptop compose file, not production) |
| SEC-014 | Dependency upgrades + CI scanning workflow |
| SEC-015 | Concurrency limits and architecture document; **not** MicroVMs |
| SEC-016 | Licensed key list/revoke/expiry/audit |
| SEC-017 | Schedule creation validates agent ownership |
| SEC-020 | Export, deletion, configurable retention field (purge job still outstanding) |
| SEC-021 | Evidence redaction |
| SEC-024 | CI workflow file; git hosting still outstanding |
| SEC-025 | Member invite and role management |
| SEC-026 | Console proxy includes `/programmes` and `/library` |
| SEC-027 | Intelligence approval is audited |

---

## 4. Outstanding infrastructure requirements

1. Place the codebase on a managed git host with `main` protected and required reviews.
2. Production: HTTPS, managed PostgreSQL, Redis with auth, Celery workers, no published database ports.
3. Store `ENCRYPTION_KEY` in a cloud KMS or secrets manager; rotate with `ENCRYPTION_KEY_PREVIOUS`.
4. Ship `aegis.security` and database backups to access-controlled storage.
5. Egress proxy and separate worker network before scaling outbound assessments; MicroVMs before any customer-code execution.
6. SMTP for password reset and invitations.
7. Observability (metrics, uptime, error budget).

## 5. Outstanding organisational requirements

1. Approve DRAFT policies.
2. Name a security owner and an incident owner.
3. Training, access reviews, vendor reviews, DR restore test, IR tabletop.
4. Independent pentest and auditor selection.
5. Customer DPA / subprocessors list consistent with actual hosting (not in this repo).

## 6. Critical unresolved risks

1. **Shared execution/control plane (SEC-015).** A parser or client bug in an agent response still runs with API/worker privileges.
2. **Untested backups (SEC-023).** Data loss is currently unrecoverable as a proven capability.
3. **No production host in this repository.** Insecure Compose defaults are improved but still for local use (`aegis-dev-only` passwords).
4. **In-process rate limiting** will not hold on multiple replicas.
5. **Master encryption key still single-tenant-derived, not KMS-held.** Compromise of the environment exposes all tenant data keys.
6. **No independent offensive test** of the new controls.

## 7. Recommended independent penetration-testing scope

Engage a tester who will not be given a “known passing” script. Scope should include:

- Authentication: credential stuffing, MFA bypass, reset poisoning, session fixation, cookie flags.
- Authorisation: IDOR across agents, assessments, programmes, reports, credentials, members, licensed keys, schedules.
- Tenant isolation: two full tenants, including export and deletion side effects.
- SSRF: agent endpoint tricks, PDF generation, webhooks, Stripe webhook replay.
- Privilege escalation: analyst → admin, last-owner removal, platform operator flag.
- Secrets: API responses, logs, PDF, evidence, client bundle.
- Execution: resource exhaustion, timeout kills, concurrency limits, sandbox breakout **if** any code execution is in scope (today: none).
- Dependency and infrastructure review of the eventual production account.

Out of scope unless customer-code execution ships: MicroVM escape.

## 8. Type I readiness roadmap

Type I tests whether controls are **suitably designed and implemented at a point in time**.

| Gate | Action |
|---|---|
| 1 | Management approves policies and the system description (services, locations, subservice organisations). |
| 2 | Production environment exists with the validated settings; MFA mandatory for administrators is on. |
| 3 | Git hosting, CI green, branch protection. |
| 4 | Independent pentest of section 7; high findings closed or accepted in writing. |
| 5 | Backup restore performed once; result recorded (pass or fail — do not claim success in advance). |
| 6 | Vendor list and Stripe/host contracts. |
| 7 | Choose auditor; walkthrough of CTRL-AC-\* and CTRL-OP-05/07 as the core Security story. |
| 8 | Type I only after the above exist **in production**, not only in this repo. |

Estimated engineering+ops elapsed time after a production host is chosen: on the order of **8–12 weeks**, dominated by hosting, pentest scheduling, and management artefacts — not by further application features. This is a planning range, not a commitment.

## 9. Type II preparation roadmap

Type II tests **operating effectiveness over a period** (commonly 3–12 months).

Start the clock only after Type I design gaps that would fail effectiveness are closed (especially backups, log shipping, access reviews, change tickets, MFA actually used by administrators).

During the period, collect:

- Quarterly access reviews
- CI records for every production deploy
- Vulnerability scan outputs and ticket SLAs
- Backup restore evidence at least once in the period
- Incident tickets (including “none this quarter”)
- MFA enrolment for all administrators
- Vendor review dates
- Training completions

Do not begin a Type II period against development laptops or unmonitored Compose.

---

## 10. Pointers

| Artefact | Path |
|---|---|
| Initial gap assessment | `security/SOC2_GAP_ASSESSMENT.md` |
| Control matrix | `security/compliance/SOC2_CONTROL_MATRIX.md` |
| Policies | `security/compliance/01`–`15` |
| Execution architecture | `security/EXECUTION_ISOLATION_ARCHITECTURE.md` |
| Backup notes | `security/BACKUP_AND_RECOVERY.md` |
| Security tests | `backend/tests/test_security.py` |
| CI | `.github/workflows/security.yml` |
