# Aegis AI — Technical Maturity Report

| | |
|---|---|
| Document status | Living engineering report |
| Started | 18 November 2026 |
| Current phase | Phase 1 complete — audit and baseline |
| Product claim | Functional multi-tenant assessment SaaS prototype; **not** production-certified; **not** SOC 2 compliant |
| Repository | `C:\Users\ADMIN\Code\aegis ai` (no git remote detected at audit time) |

This report records verified condition, weaknesses, and incremental work. It must not invent benchmark results, certification status, or untested integrations.

---

## Phase 1 — Repository audit and baseline

### 1.1 What was inspected

- Repository layout: `backend/`, `frontend/`, `security/`, `docker-compose.yml`, `.github/workflows/security.yml`, README, `.env.example`
- Security docs: `SOC2_READINESS_REPORT.md`, `SOC2_GAP_ASSESSMENT.md`, `EXECUTION_ISOLATION_ARCHITECTURE.md`, `BACKUP_AND_RECOVERY.md`, 15 draft policies, control matrix
- Backend modules: `engine/`, `scenarios/`, `sandboxes/`, `intelligence/`, `integrations/`, `reports/`, `commercial/`, `iam.py`, `security.py`, `hardening.py`, `privacy.py`, `net/ssrf.py`, `api.py`, models, Alembic migrations (7)
- Frontend: App Router public + `(console)` routes, middleware, `/api/v1` proxy, intel/site components
- Automated suites: backend pytest, frontend vitest, frontend eslint

### 1.2 Baseline test results (18 Nov 2026)

| Suite | Result | Detail |
|---|---|---|
| Backend pytest | **65 passed** | ~21.1s, Python 3.11.9, pytest 8.4.2 |
| Frontend vitest | **2 passed** | `src/lib/dashboard.test.ts` only |
| Frontend eslint | **FAILED** | 1906 errors / 25512 warnings — config does not ignore `.netlify/**` / generated trees; CI job would fail as written |
| Independent security benchmark | **Absent** | No framework, no TP/TN/FP/FN metrics |
| Hosted CI | **Not runnable here** | Tree is not a git repository; workflow exists but cannot execute against a remote |

Backend suites present: `test_stage1`–`test_stage5`, `test_industry_intelligence`, `test_security` (65 tests total).

### 1.3 Architecture as implemented (verified)

```text
Browser → Next.js (SSR + same-origin /api/v1 proxy) → FastAPI
                                                      ├─ Auth / IAM / RBAC
                                                      ├─ Agents + Fernet credentials
                                                      ├─ Assessment jobs (inline or Celery)
                                                      │    ├─ Catalogue runner (tag/heuristic judge)
                                                      │    └─ Programme / scenario runner (structured checks)
                                                      ├─ In-memory industry sandboxes
                                                      ├─ Scoring + findings + remediation
                                                      └─ PDF reports
```

**Two assessment engines coexist:**

1. **Catalogue engine** — `backend/app/engine/runner.py`  
   Single-turn prompts; judge on marker presence, forbidden tools, a few hard-coded heuristics. Tool calls may hit a sandbox, but results are **not** fed back to the agent.

2. **Scenario / programme engine** — `backend/app/scenarios/execution.py` + `evaluation.py`  
   Multi-turn workflows (up to 4 tool rounds); structured checks (`tool_not_requested`, `state_unchanged`, `marker_absent`, etc.); richer evidence and transcripts.

### 1.4 Inventory (counts verified in process)

| Asset | Count / status |
|---|---|
| Scenario library | **38** scenarios (customer_service 10, accounting 10, healthcare 6, legal 6, sales_crm 6) |
| Sandboxes | **6** (accounting, legal, retail, customer_service, healthcare, sales_crm) — **44** tools |
| Retail scenarios | **None** dedicated module (retail sandbox exists; scenarios do not cover it as an industry library) |
| Catalogue cases | 10 generic; with sandbox-specific tags: accounting/legal/retail ≈16–17 selectable |
| Runnable adapters | `openai_compatible`, `aegis_demo` |
| Registered unavailable | anthropic, azure_openai, amazon_bedrock, custom_http, n8n, langchain, crewai, custom_python |
| Result vocabulary in use | `PASS`, `FAIL`, `ERROR`, `INCONCLUSIVE`, `SKIPPED` |
| `NOT_APPLICABLE` | **Not implemented** anywhere under `backend/app` |

### 1.5 Lifecycle map

| Step | Implementation | Condition |
|---|---|---|
| Agent connection | Agents API + connection-test + SSRF-guarded outbound | Real for OpenAI-compatible; demo local |
| Profiling | `scenarios/profiling.py` + profile routes | Implemented |
| Programme configuration | Programme builder + plan JSON on assessment | Implemented |
| Scenario execution | `run_scenario` multi-turn tool loop | Implemented; round/time caps |
| Catalogue execution | `run_catalogue_case` | Weaker; single-turn; absence-PASS risk |
| Evidence | `evidence_json` + finding evidence rows; redaction via `privacy.py` | Present; quality varies by engine |
| Scoring | `intelligence/scoring.py` penalty model | Documented; can mask critical findings |
| Findings / remediation | Severity rules + remediation catalogue | Implemented |
| Reporting | PDF via ReportLab; org-scoped download | Implemented; limitations listed |
| Worker path | `commercial/jobs.py` + Celery when broker set | Queue/limits real; retry/idempotency gaps |

### 1.6 Critical correctness findings (assessment engine)

These are the highest-priority engineering risks for external pilots.

#### C1 — Catalogue judge treats silence / evasion as PASS (High)

`_judge` in `engine/runner.py` returns PASS when no markers/forbidden tools/heuristics fire. Verified:

- Empty reply → `PASS`
- Unrelated benign reply → `PASS` for a marker-tagged case

A refusal, empty response, or off-topic answer can be scored as a successful security test. This inflates true negatives and hides false negatives.

#### C2 — Dual engines with unequal rigor (High)

Programmes use structured checks; many UX paths and “generic” cases still use the catalogue judge. Pilots may mix scores that mean different things without a clear engine version boundary in the UI.

#### C3 — Aggregate score can classify “controlled” despite a critical failure (High)

Verified with the live scoring function:

- 9 PASS + 1 FAIL(critical weight 10) → **score 90 / classification `controlled`**
- 19 PASS + 1 FAIL(critical) → **score 95 / `controlled`**

A single severe vulnerability can disappear inside a high aggregate. Findings exist separately, but the headline number is misleading for pilots.

#### C4 — Partial job retry can duplicate results (High)

`run_job` increments attempts and re-enters `execute_assessment` while status may still be `running` after a crash mid-loop. There is no clear/idempotent “result set for attempt N” gate. Duplicate `AssessmentResult` rows and inflated scores are possible.

#### C5 — Catalogue path is not a closed tool loop (Medium–High)

Tool calls are executed once for judgement; tool outputs are not returned to the model. Multi-step tool manipulation cannot be tested on the catalogue path the way scenario execution does.

#### C6 — No independent Aegis-vs-Aegis benchmark (High for credibility)

No vulnerable/secure reference agents, no versioned confusion-matrix metrics, no repeatability harness. Demo agent weaknesses are planted; that is useful for UX demos, not scientific validation of Aegis detection quality.

#### C7 — Outcome taxonomy incomplete vs mission requirements (Medium)

`NOT_APPLICABLE` is required by the mission brief but absent. `SKIPPED` covers cancellation only. Profile-driven exclusions need a first-class, non-scored outcome.

### 1.7 Sandbox and isolation findings

| Topic | Condition |
|---|---|
| Synthetic data | Fictional in-memory copies via `SandboxSession` — verified |
| Role-gated tools | Explicit `roles` / deny policies — verified |
| Cross-assessment isolation | Fresh `deepcopy` per session — verified |
| Escape to host FS / network from tools | Tools are Python handlers in-process — **not** container/microVM isolated |
| Documented threat model | `security/EXECUTION_ISOLATION_ARCHITECTURE.md` correctly states limits |
| Production-grade isolation claim | **Must not be claimed** |

Retail sandbox exists without a matching industry scenario pack — coverage asymmetry.

### 1.8 Application security findings (focused)

Supplemental detail from the Phase 1 security surface audit ([security surface audit](e87457b0-69ae-451d-8571-9cfddf55df68)). Assessment-engine explore pass did not complete (provider block); engine findings above remain from direct inspection.

**Strengths observed in code/tests:**

- Argon2id passwords; hashed sessions; idle + absolute expiry; client header mutation gate (`X-Aegis-Client: web`)
- Tenant-scoped queries; cross-org 404 tests for agents, assessments/results, reports; programmes empty after org switch
- Tenant-bound Fernet credentials (`v2:`); masked responses; export/delete overwrite; redaction helpers
- SSRF controls with IP pinning / private+metadata blocks (`net/ssrf.py`); PDF markup SSRF closed with regression
- Stripe webhook signature verification when secret configured (`commercial/billing.py`) — missing signature → 400
- Hash-chained audit events (tamper-evidence limited — see below)
- MFA/TOTP, recovery codes, lockout, password reset **token hashing** paths present
- RBAC roles (`viewer` / `analyst` / `administrator` / `owner`) enforced server-side

**Gaps / risks:**

| ID | Severity | Issue |
|---|---|---|
| S1 | **High** | Auth rate limiting ineffective behind Next proxy in Compose/prod-like topologies: peer IP is the proxy; default `trusted_proxy_ips` is loopback only → `X-Forwarded-For` ignored → shared IP bucket (`api.py` `request_ip`, frontend proxy route, `config.py`) |
| S2 | **High** | Password reset / invite **email path absent** — hashed tokens created; SMTP settings unused; forgot-password UX claims a link will be sent; invite returns plaintext `invite_token` in JSON |
| S3 | **High** | Execution plane shares control-plane secrets (Celery worker same image/env/DB/encryption key); app-layer SSRF only — as documented in `EXECUTION_ISOLATION_ARCHITECTURE.md` |
| S4 | Medium | Cross-tenant negative coverage incomplete for mutate-by-id paths (findings, schedules, programmes); cross-tenant denial audit special-cased for agents |
| S5 | Medium | Audit hash-chain is application-level; without append-only external store, insider DB edit can rewrite chain |
| S6 | Medium | Rate limiting is in-process; multi-replica deployments share no limiter (related to S1) |
| S7 | Medium | Request size middleware is Content-Length-only — omit header may bypass 1 MiB check (`hardening.py`) |
| S8 | Medium | Stripe webhook trusts `metadata.organisation_id` after signature verify without customer↔org binding proof; no event idempotency store; `billing_enforce` default `False`; portal helper exists without routed API |
| S9 | Medium | Unimplemented adapters selectable in agent form — agents look configured until run fails; draft assessment form does not filter them the way the wizard does |
| S10 | Medium | Retention: `retention_days` API without purge job; legal copy says life-of-account |
| S11 | Low–Med | Frontend eslint ignores omit `.netlify/**`; CI lint step non-viable |
| S12 | Low | Frontend middleware is cookie presence only — expired sessions can show console chrome until API 401 |
| S13 | Low | Schema allows storing `http://localhost` endpoints; SSRF blocks at call time — confusing UX |
| S14 | Low | Security log scrubbing is shallow (fixed key names, not recursive) |
| S15 | Low | README SQLite-first vs compose Postgres+Redis+Celery — ops confusion |
| S16 | Info | Registry correctly marks non-OpenAI adapters unavailable; do not claim they work |

**Negative-test gaps to close in Phase 6 (from audit):** proxy-aware rate limit behaviour; Stripe positive webhook + forged-org rejection; cross-tenant mutate routes; chunked body size bypass; CSRF header absence; MFA-required admin flag on; forgot-password response must not leak reset token; schedule hook replay/rate limit.

### 1.9 Reporting and evidence integrity

**Present:** assessment id, agent metadata, dates, findings, severity, reproduction, remediation, limitations, simulated labelling.

**Gaps for pilot credibility:**

- Engine version / scenario library version not consistently first-class in all report surfaces (scenario evidence has `content_hash` / version; catalogue path weaker)
- Determinism not proven by tests for unchanged assessment → identical PDF bytes
- Catalogue PASS evidence can be thin (“matched expected behaviour”) without positive proof of refusal

### 1.10 Reliability / ops readiness

| Area | Condition |
|---|---|
| Health endpoint | `/api/v1/health` → `{api: ok}` only — **no** DB/Redis/Celery/migration checks |
| Migrations | Alembic through `20261107_0007`; API Dockerfile runs upgrade on start; worker does not migrate |
| Celery | Worker service in compose; sync fallback when no broker / test env; same secrets as API |
| Email | `smtp_*` settings present but **unused** — reset/invite delivery missing |
| Backups | Scripts exist; docs state restore **untested**; Compose volume ≠ backup system |
| Billing | Signature verify real; enforce off by default; portal not exposed |
| Deploy | Netlify frontend artefacts present; backend hosting not packaged as a production runbook in-repo |
| Production gates | `validate_production_settings` checks cookie secure, no SQLite, CORS, MFA admins, encryption key, HTTPS app URL |
| Git/CI | Workflow defined; repo not initialised/hosted here |

### 1.11 Product / UX credibility notes (no redesign)

Positive: demo pages and many console paths label **simulated**; unavailable integrations have adapter status; landing copy states observable-only limits; dashboard empty states avoid fabricated metrics.

Risks:

- Headline **numeric score bands** (`controlled` at 90+) can contradict open critical findings
- Empty/evasion catalogue PASSes look like completed secure behaviour
- Retail sandbox discoverable without industry scenario pack may look like incomplete coverage rather than intentional staging
- Unimplemented adapters still creatable in the agent form (labelled, but still look like live agents)
- Forgot-password copy implies email delivery that is not wired
- Members / billing / licensed keys / org-delete APIs exist with little or no console surface
- Frontend middleware cookie-only gate; frontend test surface tiny (2 tests)

### 1.12 Incomplete / mocked / unavailable (explicit)

| Item | Status |
|---|---|
| Non-OpenAI adapters | Registered, do not send traffic |
| Planned industries (insurance, recruitment, …) | Marked not available in reports module |
| MicroVM / dedicated execution VPC | Design only |
| Independent detection benchmark | Missing |
| `NOT_APPLICABLE` outcome | Missing |
| Hosted SIEM / KMS / shared rate limiter | Ops gaps |
| SOC 2 certification | Not claimed; readiness draft only |

### 1.13 Prioritised engineering backlog (post–Phase 1)

Ordered for correctness → credibility → security depth → ops.

1. **Fix catalogue judgement semantics** — require positive secure evidence or mark INCONCLUSIVE; never PASS on empty/untested behaviour  
2. **Score methodology** — separate finding severity from aggregate; floor/cap so critical open findings cannot yield `controlled`  
3. **Assessment job idempotency** — attempt tokens; clear or version result sets; no duplicate rows on retry  
4. **Independent benchmark harness** (30–50 cases, secure+vulnerable agents, confusion matrix, versioned results)  
5. **Unify outcome taxonomy** — add `NOT_APPLICABLE`; document mapping across engines  
6. **Evidence/report hardening** — engine + library versions; deterministic PDF tests; refuse invented claims  
7. **Sandbox audit pass** — retail scenario pack or explicit “sandbox-only” labelling; stateful workflow tests; isolation threat model linked from UI limitations  
8. **Proxy-aware rate limiting** + shared limiter plan; Content-Length-only body-size bypass  
9. **SMTP delivery or honest UX** for reset/invite (stop claiming email until wired); avoid returning invite tokens long-term without OOB channel  
10. **Cross-tenant negative test matrix expansion** (mutate paths, Stripe org binding, schedule hooks)  
11. **CI hygiene** — eslint ignores for `.netlify`; keep backend 65 green; add benchmark job later  
12. **Pilot deployment checklist** — deep health, TLS, Postgres, Redis auth, webhook secrets, SMTP, tested backups, billing_enforce decision, no false SOC2 claims; block unimplemented adapters from looking operational  

### 1.14 Phase 1 changes made

- Created and updated this report at `exports/AEGIS_TECHNICAL_MATURITY_REPORT.md`
- Merged supplemental findings from [security surface audit](e87457b0-69ae-451d-8571-9cfddf55df68)
- **No application code changes** in Phase 1 (audit-only, per mission)

### 1.15 Tests executed (Phase 1)

- `backend`: `pytest -v` → **65 passed**
- `frontend`: `npm test` → **2 passed**
- `frontend`: `npm run lint` → **failed** (ignore/path scope issue)

### 1.16 Unresolved issues after Phase 1

All items in §1.6–§1.12 remain open. No regressions introduced (no code edits).

### 1.17 Next phase priorities (Phase 2)

**Phase 2 — Assessment engine correctness** (do not start Phase 3 until these land):

1. Catalogue `_judge` / result semantics: PASS only with positive secure evidence; infrastructure → ERROR; unobservable → INCONCLUSIVE  
2. Idempotent assessment execution and completion state machine  
3. Regression tests for empty-reply, timeout, tools_unsupported, cancel, partial failure  
4. Clear engine identifier in every stored result (`catalogue` vs `scenario`)  
5. Keep existing scenario evaluator behaviour unless a concrete false PASS/FAIL is proven  

---

## Later phases (planned; not started)

| Phase | Focus |
|---|---|
| 3 | Independent security benchmark |
| 4 | Scoring + evidence integrity |
| 5 | Sandbox security + isolation documentation/tests |
| 6 | Application security hardening |
| 7 | Reliability / operational readiness |
| 8 | UX credibility + documentation |
| 9 | Full regression + final verification |

---

## Change log

| Date | Phase | Summary |
|---|---|---|
| 2026-11-18 | 1 | Baseline audit; 65 backend / 2 frontend tests recorded; prioritised backlog written; no product code changes |
| 2026-11-18 | 1 | Incorporated [security surface audit](e87457b0-69ae-451d-8571-9cfddf55df68): raised S1–S3 (proxy rate limit, SMTP gap, shared execution plane); expanded S4–S16, ops table, UX risks, backlog items 8–12 |
