# Aegis AI — Security and SOC 2 Gap Assessment

| | |
|---|---|
| Document status | DRAFT — technical assessment, not an audit opinion |
| Assessment date | 3 November 2026 |
| Scope | Repository at `aegis ai/` (backend, frontend, worker, compose, configuration) |
| Framework | AICPA Trust Services Criteria (2017, revised points of focus 2022), Security category primarily |
| Assessor | Engineering (internal). Not independent. |

Aegis AI is **not SOC 2 compliant or certified**. This document records the state of the codebase as found at the start of the readiness programme. The status column reflects what was verified in code and by execution **before** remediation. Post-remediation status is tracked in `security/SOC2_READINESS_REPORT.md` and `security/compliance/SOC2_CONTROL_MATRIX.md`.

---

## 1. Method

1. Read every backend module that handles identity, sessions, authorisation, credentials, outbound requests, reporting, billing, webhooks, licensed API access, and assessment execution.
2. Read the frontend proxy, route guard, API proxy route, and all places agent-controlled text is rendered.
3. Read `docker-compose.yml`, both Dockerfiles, `.env.example`, `.gitignore`, and dependency manifests.
4. Executed:
   - `pip-audit -r backend/requirements.txt` — **15 known vulnerabilities in 3 packages** (see SEC-014).
   - `npm audit --omit=dev` — 0 production vulnerabilities.
   - `bandit -r backend/app -ll` — no medium or high findings.
   - `security/scripts/secret_scan.py` — one hit, a deliberate test fixture (`backend/tests/test_stage1.py`), now annotated.
   - A targeted proof for SEC-004 (ReportLab markup) that observed an outbound connection attempt to `169.254.169.254:80` from report generation.
5. Checked whether the project is under version control: **it is not a git repository** (SEC-024).

"Implemented" below means the behaviour was verified in code or by a test, not that an interface or setting exists.

---

## 2. Architecture as found

| Area | Finding |
|---|---|
| Frontend | Next.js 16 (App Router). Browser calls same-origin `/api/v1/*`; a route handler (`src/app/api/v1/[...path]/route.ts`) proxies to FastAPI and forwards cookies. `src/proxy.ts` redirects unauthenticated users for some console routes (UX only). |
| Backend | FastAPI, SQLAlchemy 2, Alembic (migrations 0001–0006). SQLite in development, PostgreSQL in Compose. |
| Worker | Celery worker using the **same image, same environment, same database credentials, same encryption key** as the API. Without a broker, jobs run in-process in the API request. |
| Authentication | Email and password, Argon2id (`argon2-cffi` defaults). Opaque session token (32 bytes, `secrets.token_urlsafe`), SHA-256 hash stored, `HttpOnly` cookie, `SameSite=Lax`, `Secure` configurable (default **false**). 12-hour absolute expiry. Logout revokes the server-side session. |
| CSRF | Mutating requests require header `X-Aegis-Client: web`; CORS allows only configured origins. A custom header cannot be sent cross-site without a CORS preflight, so this is an effective CSRF control. |
| Authorisation | Roles `owner`, `administrator`, `analyst`, `viewer` (`admin`/`member` aliases). Checked server-side per route with `require_role`. Platform operator flag on `users` gates operator endpoints. |
| Tenancy | Single database, shared schema. Every tenant table has `organisation_id`; service functions filter on the organisation from the **session**, not from client input. The session is bound to one organisation. |
| Customer agent connection | `openai_compatible` adapter calls the customer's HTTPS endpoint with the customer's API key as a Bearer token. `aegis_demo` runs locally. Other adapters are listed but not implemented. |
| Where tests execute | Aegis does **not** run customer code. Assessments send prompts to the customer's remote endpoint. "Tools" are Python functions operating on an in-memory deep copy of synthetic data inside the API or worker process. |
| Credentials | Agent API keys encrypted with Fernet using one `ENCRYPTION_KEY` from the environment; last 4 characters kept as a hint; never returned by the API; destroyed (ciphertext overwritten) on rotation or deletion. |
| Evidence and results | Stored in the database (`assessment_results.evidence_json`, `finding_evidence`). PDFs stored as `LargeBinary` in `reports`. No file uploads exist anywhere in the product. |
| Logging | Python `logging.basicConfig` plain text to stdout. `audit_events` table written for many actions; members of the organisation can read the latest 20. |
| Deployment | `docker-compose.yml` for local use. No IaC, no CI, no backups, no TLS termination in-repo. |

---

## 3. Findings

Severity uses likelihood × impact for a multi-tenant SaaS that holds customers' AI provider credentials.

### Critical

#### SEC-004 — Agent-controlled text is interpreted as markup in PDF reports, enabling SSRF to cloud metadata
- **Description:** `reports/pdf.py` passes finding text, including the agent's observable response (`finding_evidence.content`), into ReportLab `Paragraph` without escaping. ReportLab interprets markup. `<img src="http://169.254.169.254/...">` causes the backend to open a connection to that address; unbalanced tags raise and abort report generation. This was **reproduced**: the proof recorded a connection attempt to `169.254.169.254:80`.
- **Affected component:** `backend/app/reports/pdf.py`, `reports/service.py`.
- **Business impact:** Any agent under test (untrusted by definition) can trigger server-side requests from the control plane to internal services or the cloud metadata endpoint, bypassing the SSRF guard entirely, and can break report generation for the tenant.
- **Remediation:** Escape all dynamic text before it reaches ReportLab, restrict ReportLab's trusted schemes, add a regression test with hostile markup.
- **Status at assessment:** Missing.

### High

#### SEC-001 — An analyst can redirect a stored credential to an attacker-controlled endpoint
- **Description:** Storing or rotating a credential requires an administrator, but `PATCH /agents/{id}` (analyst and above) can change `api_endpoint` to any public HTTPS host while the stored credential stays attached. The next connection test or assessment sends the administrator-stored key as `Authorization: Bearer` to the new host.
- **Affected component:** `api.py` `update_agent_route`, `services.update_agent`, `integrations/openai_chat.py`.
- **Business impact:** Disclosure of customers' AI provider keys to a lower-privileged insider or a compromised analyst account; financial loss on the provider account.
- **Remediation:** Require the administrator role to change the endpoint origin, and revoke (destroy) the stored credential whenever the origin changes. Audit the event.
- **Status:** Missing.

#### SEC-002 — Login rate limiting keys on the proxy address and is per-process
- **Description:** `enforce_rate_limit` buckets by `request.client.host`. All browser traffic arrives through the Next.js proxy, so every user shares one bucket: 20 login attempts per 10 minutes across the platform. The limiter is an in-memory dict, so it resets on restart and does not apply across instances. There is no per-account lockout. Audit `ip_address` values record the proxy, not the user.
- **Affected component:** `api.py` `enforce_rate_limit`, `services.client_ip`, frontend API proxy.
- **Business impact:** A single attacker can lock out all logins (availability), while brute force against one account is only limited platform-wide. Audit evidence lacks real client IPs.
- **Remediation:** Trust `X-Forwarded-For` only from configured proxy addresses; rate limit per client IP and per account; persistent per-account lockout with backoff; audit lockouts.
- **Status:** Partially implemented (limiter exists but is ineffective behind the proxy).

#### SEC-003 — SSRF guard patches DNS resolution process-wide and buffers unbounded responses
- **Description:** `net/ssrf.py` replaces `socket.getaddrinfo` globally while an outbound call is in progress, under a global lock. Other threads resolving hostnames during that window (database, Redis, Stripe) are subject to the "blocked destination" check and fail if they resolve to private addresses, which they do in any VPC. The global lock serialises every agent call platform-wide. `response.content` is read fully before the size check.
- **Affected component:** `backend/app/net/ssrf.py`.
- **Business impact:** Intermittent outages under concurrency; one slow customer endpoint blocks every other tenant's assessments; memory exhaustion from large responses.
- **Remediation:** Resolve once, validate every address, connect to the validated IP with TLS SNI and certificate verification against the original hostname, stream the body with a hard byte cap, remove the global patch and lock.
- **Status:** Partially implemented (validation is good; enforcement mechanism is unsafe).

#### SEC-005 — No multi-factor authentication
- **Description:** No MFA of any kind. Administrators who can store credentials, delete agents, change consent, and create webhooks authenticate with a password only.
- **Affected component:** Identity.
- **Business impact:** Credential stuffing or phishing of an administrator gives full tenant control and access to stored provider keys (via SEC-001-style abuse or assessments).
- **Remediation:** TOTP MFA with encrypted secrets and hashed recovery codes; two-step login; mandatory for owners and administrators before administrative actions.
- **Status:** Missing.

#### SEC-013 — Container and Compose configuration is insecure by default
- **Description:** Hardcoded PostgreSQL credentials (`aegis/aegis`) in `docker-compose.yml`; PostgreSQL and Redis published on all host interfaces; Redis without authentication; both images run as root; no resource limits; no read-only filesystems.
- **Affected component:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`.
- **Business impact:** If this Compose file is used beyond a laptop, the database and broker are reachable with known or no credentials.
- **Remediation:** Environment-provided credentials, loopback-only port binding, Redis `requirepass`, non-root users, `no-new-privileges`, resource limits; production on managed services.
- **Status:** Missing.

#### SEC-014 — Dependencies with known vulnerabilities
- **Description:** `pip-audit` reports `cryptography 44.0.0` (7 advisories, fixed up to 50.0.0), `starlette 0.41.3` via `fastapi 0.115.6` (7 advisories), `pytest 8.3.4` (1). No dependency scanning in any pipeline.
- **Affected component:** `backend/requirements.txt`.
- **Business impact:** Known, published vulnerabilities in the HTTP framework and cryptographic library.
- **Remediation:** Upgrade and pin; add `pip-audit` and `npm audit` to CI with a blocking threshold.
- **Status:** Missing.

#### SEC-015 — No separation between control plane and execution activity
- **Description:** Agent requests are made by the API process (in-process jobs) or a Celery worker that shares the API's image, network, database credentials, and encryption key. There is no egress allowlist, no per-tenant concurrency limit, and no plan-size limit beyond billing quotas. Aegis does not execute customer code today, which lowers but does not remove the risk: the outbound HTTP client and the response parser handle hostile input.
- **Affected component:** `engine/runner.py`, `scenarios/execution.py`, `commercial/jobs.py`, Compose.
- **Business impact:** A parser or client vulnerability triggered by a hostile agent response would execute with full control-plane privileges. One tenant can consume worker capacity for everyone.
- **Remediation:** In code: per-tenant and global concurrency limits, bounded plans, outbound allowlist support, short-lived credential handling. In infrastructure: a dedicated execution worker pool in its own network segment with deny-by-default egress via an allowlisting proxy, no database superuser rights, and IMDS disabled. MicroVM isolation becomes mandatory if customer code execution is ever introduced.
- **Status:** Missing.

#### SEC-023 — No backups or disaster recovery
- **Description:** No backup job, no backup encryption, no restore procedure, no RTO/RPO.
- **Affected component:** Operations.
- **Business impact:** Data loss is unrecoverable.
- **Remediation:** Encrypted automated backups (managed PostgreSQL PITR in production), a scripted backup and restore, scheduled restoration tests with recorded evidence.
- **Status:** Missing.

#### SEC-024 — No version control, CI, code review, or change management
- **Description:** The project directory is not a git repository. There is no CI, no branch protection, no review record, no release record.
- **Affected component:** Development process.
- **Business impact:** No evidence for CC8.1 (change management); no ability to roll back; no automated security gates.
- **Remediation:** Initialise a repository on a managed host with protected branches and required reviews; add a CI security workflow; adopt the change-management procedure.
- **Status:** Missing.

### Medium

#### SEC-006 — No password reset procedure
- **Description:** No reset flow. A user who forgets a password has no secure recovery path, which pushes operators towards ad hoc database edits.
- **Remediation:** Single-use, hashed, 30-minute reset tokens; uniform responses to prevent enumeration; revoke all sessions on reset; audit; deliver by email only.
- **Status:** Missing.

#### SEC-007 — Session lifecycle gaps
- **Description:** Sessions are not revoked on password change, there is no idle timeout, no way to list or revoke other sessions, and expired rows are never purged.
- **Remediation:** Revoke other sessions on password change and reset; idle timeout; session list and revoke endpoints; retention purge.
- **Status:** Partially implemented (absolute expiry and logout revocation exist).

#### SEC-008 — Audit trail integrity and access
- **Description:** `audit_events` rows are ordinary mutable rows with no integrity protection; any member including `viewer` can read them; failed authorisation attempts (403) and cross-tenant probes (404 on another tenant's object) are not recorded; there is no separate security log stream.
- **Remediation:** Hash-chained audit events with a verification routine; restrict audit access to administrators; record authorisation failures; structured JSON security log on a dedicated logger; ship to append-only storage in production.
- **Status:** Partially implemented.

#### SEC-009 — No HTTP security headers
- **Description:** Neither the Next.js app nor the API sets CSP, HSTS, `X-Frame-Options`/`frame-ancestors`, `X-Content-Type-Options`, `Referrer-Policy`, or `Permissions-Policy`.
- **Remediation:** Add headers in `next.config.ts` and API middleware.
- **Status:** Missing.

#### SEC-010 — No request size limits
- **Description:** The API accepts arbitrarily large bodies; Pydantic limits individual fields but parsing happens first.
- **Remediation:** Reject bodies over a configured limit before parsing.
- **Status:** Missing.

#### SEC-011 — Single static encryption key, no tenant separation or rotation
- **Description:** One Fernet key encrypts all tenants' credentials. No key identifier, no rotation path, no re-encryption tooling, no KMS.
- **Remediation:** Per-tenant data keys derived from the master key (HKDF with the organisation identifier), versioned ciphertext, `MultiFernet` rotation across master keys, re-encryption command; KMS-held master key in production.
- **Status:** Partially implemented (encryption at rest exists).

#### SEC-012 — Insecure defaults and no production configuration validation
- **Description:** `COOKIE_SECURE` defaults to false; nothing prevents production start-up with SQLite, insecure cookies, an example encryption key, or wildcard CORS.
- **Remediation:** Refuse to start in production with insecure settings.
- **Status:** Missing.

#### SEC-016 — Licensed API keys and webhook tokens cannot be listed, expired, or revoked
- **Description:** Keys are hashed (good) but have no expiry, no revocation endpoint, and creation is not audited.
- **Remediation:** List, revoke, and expiry for both; audit creation and use.
- **Status:** Partially implemented.

#### SEC-020 — No retention enforcement, export, or tenant deletion
- **Description:** Retention is described in a draft legal page but nothing enforces it. No organisation-level export or deletion.
- **Remediation:** Configurable retention with a purge routine; owner-initiated export and deletion with audit; documented deletion workflow.
- **Status:** Missing.

#### SEC-021 — Evidence can retain secrets echoed by an agent
- **Description:** If an agent echoes its own API key or other credentials, the text is stored verbatim in evidence and reports.
- **Remediation:** Redact the stored credential value and common secret formats from evidence before storage.
- **Status:** Missing.

#### SEC-022 — No structured security logging or alerting
- **Description:** Plain text logs; no alert rules; no detection of brute force, cross-tenant probing, or unusual execution behaviour.
- **Remediation:** Structured security events on a separate logger; in-app detection that raises notifications for lockouts, cross-tenant probes, and repeated sandbox denials; SIEM forwarding in production.
- **Status:** Missing.

#### SEC-025 — Roles cannot be assigned
- **Description:** The role model exists but there is no way to add members or change roles, so every organisation is a single owner. Least privilege cannot be practised and access reviews have nothing to review.
- **Remediation:** Member management with privilege-escalation guards (cannot grant above own role, cannot remove the last owner), MFA for role changes, audit.
- **Status:** Partially implemented.

#### SEC-027 — Platform operator actions lack MFA and audit
- **Description:** `is_platform_operator` is set directly in the database; approvals of intelligence records are not audited.
- **Remediation:** Require MFA for operator endpoints; audit approvals; document provisioning.
- **Status:** Partially implemented.

### Low

| ID | Description | Remediation | Status |
|---|---|---|---|
| SEC-017 | Schedule creation accepts an `agent_id` from another tenant (blocked later at execution by tenant-scoped lookup). | Validate ownership at creation. | Partially implemented |
| SEC-018 | Several endpoints accept untyped `dict` payloads (schedules, finding status, compare, contribute, demo profile, licensed keys, checkout). | Pydantic models with bounds. | Partially implemented |
| SEC-019 | Registration returns 409 for an existing email, enabling account enumeration. | Accept the limitation with rate limiting, or move to email verification. Documented. | Accepted risk (documented) |
| SEC-026 | Frontend route guard omits `/programmes` and `/library`. UX only; the backend enforces authentication. | Add prefixes. | Partially implemented |

### Verified existing controls (positive findings)

| Control | Evidence |
|---|---|
| Argon2id password hashing, constant-time dummy verification for unknown users | `security.py`, `services.authenticate` |
| Opaque, hashed, revocable server-side sessions in `HttpOnly` cookies | `security.py`, `services.issue_session/resolve_session`, tests in `test_stage1.py` |
| CSRF protection via required custom header and restrictive CORS | `api.enforce_client_header`, `main.py` |
| Tenant-scoped queries using the session's organisation | Service functions; tests in `test_stage1.py` and `test_industry_intelligence.py` |
| Credentials encrypted at rest, never returned, destroyed on rotation/deletion | `services.store_credential`, `delete_credential`, tests |
| SSRF validation of agent endpoints (scheme, port, private/reserved ranges, alternate IP encodings, DNS re-check) | `net/ssrf.py`, `test_stage2.py` |
| Generic error responses; no stack traces to clients; API docs disabled in production | `errors.py`, `main.py` |
| Stripe webhook signature verification | `commercial/billing.verify_webhook` |
| Synthetic-only sandbox data, deep-copied per execution | `sandboxes/runtime.py`, tests |
| Data contribution requires explicit consent | `intelligence/pipeline.py`, tests |

---

## 4. Not applicable or not present

- **File uploads:** the product has no upload feature. Generated PDF reports are the only stored files; they live in the database, scoped by organisation. Isolation tests cover reports.
- **Customer code execution:** none today. MicroVM isolation is therefore not required for current functionality but is a hard prerequisite for any future feature that runs customer code or customer-provided tools (documented in `security/EXECUTION_ISOLATION_ARCHITECTURE.md`).

---

## 5. Prioritised remediation order

1. SEC-004 PDF markup SSRF (Critical).
2. SEC-001 credential redirection.
3. SEC-014 vulnerable dependencies.
4. SEC-003 SSRF enforcement mechanism.
5. SEC-002 rate limiting and lockout.
6. SEC-005 MFA, SEC-007 sessions, SEC-006 reset.
7. SEC-009, SEC-010, SEC-012 headers, limits, and production configuration validation.
8. SEC-008, SEC-022 audit integrity, security logging, and detection.
9. SEC-011 key separation and rotation; SEC-021 evidence redaction.
10. SEC-016, SEC-017, SEC-018, SEC-025, SEC-027 access-lifecycle gaps.
11. SEC-015 execution limits in code, plus the documented infrastructure architecture.
12. SEC-020 retention, export, and deletion.
13. SEC-013 Compose and container hardening; SEC-023 backup scripts; SEC-024 CI workflow.
