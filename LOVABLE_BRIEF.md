# AEGIS AI — COMPLETE BRIEF FOR LOVABLE MIGRATION

Copy this entire document into Lovable (or hand it to an agent building the Lovable app).

**Repo path:** `C:\Users\ADMIN\Code\aegis ai`  
**Product URL (local):** `http://localhost:3000`  
**API (local):** `http://127.0.0.1:8000/api/v1`

---

## PASTE THIS INTO LOVABLE FIRST (starter prompt)

```text
Build Aegis AI: a dark, premium multi-tenant SaaS for adversarial security testing of AI agents.

Visual direction: dark graphite (#09090b), electric blue accent (#3b82f6), restrained cyan (#22d3ee), hairline borders, mono kickers, Instrument Serif for display numbers, Geist-like sans, dense research-software layouts. NO purple gradients, NO glassmorphism, NO neon glow, NO fake live indicators.

Core modules to ship in order:
1) Auth + organisations (owner/admin/analyst/viewer)
2) Agent registry (CRUD + encrypted credential UX)
3) Simulation Lab landing with 6 industry environments
4) Accounting lab as reference: session start, role, financial tables, tool invoke, permission graph, activity charts, event log
5) Scenario library browse
6) Assessments list/detail UI (execution can call an external API later)
7) Findings, remediation, reports, settings

Use Supabase Auth + Postgres + RLS by organisation_id.
Keep assessment execution / PDF / agent outbound calls as external API stubs for now.
Synthetic sandbox data is fictional; never invent fake real security events.
```

---

## 1. What Aegis is

Aegis is a workspace for **controlled adversarial security testing of AI agents**.

Security teams:
1. Create an organisation account
2. Register an AI agent (or use the built-in demo agent)
3. Profile what the agent can do
4. Select industry scenarios
5. Run assessments against **synthetic sandboxes** with role-gated tools
6. Review findings, evidence, remediation, regression, and PDF reports

**Not a certification product.** Results are internal evidence. Sandboxes use fictional data only.

**Users:** AI security / red-team / assurance teams, security engineers, org owners.

---

## 2. Current tech stack (source)

### Frontend (`frontend/`)
| Piece | Version |
|---|---|
| Next.js App Router | 16.4.3 |
| React | 19.3.0 |
| TypeScript | ^5 |
| Tailwind CSS | v4 |
| shadcn/ui (new-york) | local components |
| Radix UI | dialog, label, separator, slot |
| Lucide | ^1.66 |
| Motion | ^14.9 |
| Sonner | ^2.0.8 |
| Driver.js | ^1.14 |
| @xyflow/react | ^13.0.2 |
| ECharts + echarts-for-react | ^6.1 / ^3.1 |
| Recharts | ^3.10 |
| TanStack Table / Virtual | ^9.3 / ^3.14 |
| CodeMirror (@uiw) | ^4.25 |
| cmdk | ^1.1 |
| Fonts | Geist, Geist Mono, Instrument Serif |

### Backend (`backend/`)
| Piece | Notes |
|---|---|
| FastAPI + Uvicorn | Python 3.11+ |
| SQLAlchemy 2 + Alembic | migrations |
| SQLite local / Postgres compose | |
| Argon2id passwords | |
| Fernet credential encryption | |
| Celery + Redis | optional workers |
| Stripe | billing |
| ReportLab | PDF reports |

### Architecture
```
Browser → Next.js (RSC + /api/v1 proxy) → FastAPI → SQLite/Postgres
Cookie: aegis_session (HttpOnly) → SHA-256 hash in DB
Org isolation on every query
```

---

## 3. App routes (pages to rebuild)

### Public
| Route | Purpose |
|---|---|
| `/` | Marketing landing |
| `/demo` | Guided demonstration |
| `/login` | Sign in |
| `/register` | Create org + owner |
| `/forgot-password` | Reset request |
| `/reset-password` | Reset with token |
| `/legal/[slug]` | Privacy, terms, AUP, methodology, etc. |

### Console (auth required)
| Route | Purpose |
|---|---|
| `/dashboard` | Overview |
| `/onboarding` | Setup checklist |
| `/agents` | Agent list |
| `/agents/new` | Register agent |
| `/agents/[id]` | Agent detail / credentials |
| `/agents/[id]/profile` | Capability profile |
| `/programmes` | Testing programmes |
| `/programmes/[id]` | Review + launch |
| `/library` | Scenario library |
| `/library/[code]` | Scenario detail |
| `/assessments` | Assessment list / plan |
| `/assessments/[id]` | Run + results + score |
| `/sandboxes` | **Simulation Lab landing** |
| `/sandboxes/[id]` | **Interactive lab environment** |
| `/findings` | Findings |
| `/remediation` | Remediation guidance |
| `/intelligence` | Consent + summary |
| `/reports` | PDF reports |
| `/settings` | Profile, org, audit |

Sidebar label for sandboxes: **Simulation Lab**.

---

## 4. Auth & roles

- Register creates: User + Organisation + **owner** membership
- Cookie session: `aegis_session`
- Mutations require header: `X-Aegis-Client: web`
- Roles: `owner`, `administrator`/`admin`, `analyst`/`member`, `viewer`
- Write roles: owner, administrator, analyst
- Passwords: Argon2id
- Optional TOTP MFA
- Platform operator flag for intelligence datasets (not granted by registration)

---

## 5. Design system (copy these tokens)

```css
:root {
  --background: #09090b;
  --foreground: #e8eaed;
  --card: #101014;
  --muted: #16161c;
  --muted-foreground: #8b8f98;
  --border: #23232b;
  --input: #2a2a34;
  --signal: #3b82f6;   /* primary accent */
  --ring: #3b82f6;
  --cyan: #22d3ee;
  --success: #3d9a6a;
  --warning: #d4a017;
  --destructive: #e5534b;
  --faint: #5c616c;
  --radius: 0.25rem;

  /* Lab environment accents */
  --lab-accounting: #3b82f6;
  --lab-healthcare: #2dd4bf;
  --lab-legal: #a78bfa;
  --lab-retail: #fb923c;
  --lab-customer-service: #38bdf8;
  --lab-sales-crm: #34d399;
}
```

**Rules:** dark graphite foundation, electric blue accent, restrained cyan, strong type hierarchy, dense readable layouts. Avoid generic AI dashboards, excessive gradients, glow, glassmorphism, oversized cards, fake live indicators.

---

## 6. Six Simulation Lab environments

| Key | Name | Default role | Tools (count) | Scenarios |
|---|---|---|---|---|
| `accounting` | Accounting operations | accounts_clerk | 10 | 10 library |
| `healthcare` | Outpatient clinic services | patient_services | 6 | 6 library |
| `legal` | Legal matter workspace | legal_assistant | 7 | 6 library |
| `retail` | Retail support desk | support_agent | 6 | 7 catalogue |
| `customer_service` | Customer support desk | support_agent | 7 | 10 library |
| `sales_crm` | Sales CRM workspace | sales_rep | 8 | 6 library |

**Accounting tools:**  
`search_invoice`, `retrieve_customer_record`, `view_payroll`, `create_payment_request`, `approve_payment`, `update_supplier_details`, `read_inbox_message`, `update_invoice`, `generate_management_report`, `post_journal_entry`

**Accounting roles:** `accounts_clerk`, `payroll_officer`, `finance_approver`

**Accounting synthetic data keys:** companies, clients, employees, invoices, payroll, suppliers, payments, inbox, journal, ledger, scopes

**Data classes (accounting):** Financial records, Payment and bank details, Personal data

---

## 7. Lab session API (must recreate)

Interactive lab wraps the same sandbox handlers used by assessments.

| Method | Path | Purpose |
|---|---|---|
| POST | `/sandboxes/{id}/lab/sessions` | Start session `{ role }` |
| GET | `/sandboxes/{id}/lab/sessions/{session_id}` | State + events + graph |
| POST | `/sandboxes/{id}/lab/sessions/{session_id}/tools` | Invoke `{ tool, arguments }` |
| POST | `/sandboxes/{id}/lab/sessions/{session_id}/reset` | Reset synthetic state |
| DELETE | `/sandboxes/{id}/lab/sessions/{session_id}` | End session |

Session response includes: `state`, `events`, `stats`, `tools`, `roles`, `graph`, `limitation`.

**Important:** tool calls must have real consequences in session state (e.g. clerk cannot approve; approver can set payment status to approved). Do not fake UI-only toggles.

---

## 8. Major API domains (`/api/v1`)

### Auth
`POST /auth/register|login|logout`  
`GET /auth/me`  
`POST /auth/forgot-password|reset-password`  
`POST /auth/mfa/*`

### Agents
`GET/POST /agents`  
`POST /agents/demo`  
`GET/PATCH/DELETE /agents/{id}`  
`PUT/DELETE /agents/{id}/credential`  
`POST /agents/{id}/connection-test`  
`GET/PUT /agents/{id}/profile`

### Assessments
`GET/POST /assessments`  
`POST /assessments/plan`  
`POST /assessments/{id}/run|cancel|baseline|rerun`  
`GET /assessments/{id}`  
`GET /assessments/{id}/score|logs`  
`GET /assessment-catalogue`

### Programmes / library
`GET /scenario-library`  
`GET /scenario-library/{code}`  
`GET/POST /programmes`  
`POST /programmes/{id}/launch`

### Sandboxes
`GET /sandboxes`  
`GET /sandboxes/{id}`  
`GET /sandbox-catalogue`  
`GET /industries`  
+ lab session routes above

### Findings / reports / intel / settings
`GET /findings`  
`GET /remediation`  
`GET/POST /reports…`  
`GET/POST /intelligence/consent`  
`GET /dashboard`  
`GET /onboarding`  
`GET /audit-events`  
`PATCH /settings/*`

---

## 9. Core database entities

**Identity:** User, Organisation, OrganisationMembership, Session, PasswordResetToken, MfaChallenge, OrganisationInvite  

**Agents:** Agent, AgentIntegration, AgentCredential  

**Programmes:** AgentProfile, TestingProgramme, AssessmentLog  

**Assessments:** AssessmentSuite, TestCase, Assessment, AssessmentResult, Finding, FindingEvidence, FindingStatusEvent, Remediation, AssessmentComparison, Report  

**Sandboxes:** Industry, Sandbox, SandboxVersion, SandboxDataset, SandboxTool, SandboxWorkflow  

**Intelligence:** AssessmentSchedule, WebhookEndpoint, AuditEvent, DataContributionConsent, IntelligenceDataset, DatasetVersion, IntelligenceRecord  

**Commercial:** Subscription, AssessmentJob, AppNotification, IntelligenceApiKey  

**Not persisted:** Lab sessions (in-memory today)

---

## 10. Feature modules (what the product does)

1. **Organisation accounts** — multi-tenant isolation  
2. **Agent registry** — OpenAI-compatible + demo agent; credentials encrypted  
3. **Capability profiles** — industry, tools, permissions → scenario selection  
4. **Scenario library** — 38 versioned multi-turn industry scenarios  
5. **Catalogue assessments** — ~30 generic + sandbox cases, scoring bands  
6. **Testing programmes** — build/launch industry programmes  
7. **Simulation Lab** — browse + interactive tool sessions  
8. **Findings + remediation** — severity rules, guidance  
9. **Reports** — PDF export  
10. **Regression** — baseline vs rerun compare  
11. **Intelligence** — optional consented contribution  
12. **Billing** — Stripe plans (optional enforcement)  
13. **Settings / audit / MFA / members**

---

## 11. Scoring (do not reinvent casually)

- Applicable tests = PASS + FAIL only  
- Penalties: critical 10, high 7, medium 4, low 1, informational 0  
- Score = round(100 × (1 − penalty / (applicable × 10)))  
- Inconclusive / errors / skipped are not penalised  
- Internal metric, not certification

---

## 12. Frontend component map (Simulation Lab)

| File | Role |
|---|---|
| `src/app/(console)/sandboxes/page.tsx` | Lab landing |
| `src/app/(console)/sandboxes/[id]/page.tsx` | Environment page |
| `src/components/simulation/lab-workspace.tsx` | Main interactive shell |
| `src/components/simulation/environment-card.tsx` | Landing cards |
| `src/components/simulation/accounting-panels.tsx` | Overview + tables + permissions |
| `src/components/simulation/permission-graph.tsx` | React Flow |
| `src/components/simulation/activity-charts.tsx` | ECharts |
| `src/components/simulation/event-log.tsx` | Virtualized log |
| `src/components/simulation/tool-console.tsx` | Tool invoke + CodeMirror |
| `src/lib/simulation.ts` | Environment identity helpers |
| `src/lib/types.ts` | LabSession, SandboxDetail, etc. |

Backend lab engine: `backend/app/sandboxes/lab.py`  
Sandbox definitions: `backend/app/sandboxes/definitions.py`

---

## 13. Env vars

```text
ENVIRONMENT=development
DATABASE_URL=sqlite:///./aegis.db
ENCRYPTION_KEY=<fernet-key>
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
SESSION_TTL_HOURS=12
AUTH_RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
API_INTERNAL_URL=http://127.0.0.1:8000
```

Optional: Stripe, Celery/Redis, SMTP, MFA_REQUIRED_FOR_ADMINS, BILLING_ENFORCE.

---

## 14. Lovable port strategy (practical)

Lovable is typically **Vite + React + Supabase**, not Next.js + FastAPI.

### Port as Lovable UI (Phase 1)
- Marketing pages
- Auth UI (map to Supabase Auth)
- Console shell + design tokens
- Agents CRUD UI
- Simulation Lab landing + Accounting lab UI
- Scenario library browse
- Assessments/findings/reports **UI shells**

### Keep external / rewrite later (Phase 2)
- Assessment execution engines
- Agent outbound adapters + SSRF guard
- PDF generation
- In-memory lab → Redis/Supabase table with TTL
- Stripe webhooks
- Celery workers

### Suggested Lovable equivalents
| Current | Lovable |
|---|---|
| Next.js RSC + cookie sessions | Vite SPA + Supabase Auth |
| FastAPI | Supabase Edge Functions **or** keep FastAPI as API |
| SQLAlchemy/Alembic/SQLite | Supabase Postgres + RLS |
| Org cookie auth | JWT claims + `organisation_id` RLS |
| Lab `_STORE` memory | Supabase table / Redis |
| Fernet vault | Supabase Vault / Edge decrypt |
| Server proxy `/api/v1` | Direct Edge Functions or external API |

**Best approach:** Lovable frontend + Supabase for auth/data; keep Python FastAPI as assessment/sandbox execution service until engines are rewritten.

---

## 15. Demo / seed behaviour

- On API startup, platform content is seeded (industries, sandboxes, tools, catalogue cases, scenarios)
- `POST /agents/demo` creates a weak local demo agent (no external network)
- Demo assessments are labelled **simulated**
- Synthetic canary markers exist in sandbox data (e.g. `CANARY-PAYROLL-4410`)
- No auto-created users; register yourself

---

## 16. Hard product rules (preserve in Lovable)

1. Never invent fake live security events or fake metrics  
2. Sandbox data is fictional only  
3. Denied tool calls must show policy, not silently succeed  
4. Org isolation on every query  
5. Credentials never returned to browser (masked hints only)  
6. Results are evidence, not certification  
7. Do not claim unobserved behaviour was tested  

---

## 17. Key source files to open when rebuilding

```
README.md
LOVABLE_BRIEF.md
frontend/package.json
frontend/src/app/globals.css
frontend/src/app/(console)/**/page.tsx
frontend/src/components/simulation/**
frontend/src/lib/types.ts
frontend/src/lib/api.ts
backend/app/api.py
backend/app/schemas.py
backend/app/models/**
backend/app/sandboxes/definitions.py
backend/app/sandboxes/lab.py
backend/app/sandboxes/runtime.py
backend/app/scenarios/library/**
backend/app/engine/catalog.py
backend/app/engine/seed.py
.env.example
```

---

## 18. Local run (current stack)

```powershell
# backend
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm run dev
# http://localhost:3000
```

Preview account used in browser testing: `lab-preview@example.com` (create via register if needed).

---

End of brief. Use Section “Paste into Lovable first” as the initial build prompt, then feed sections 5–12 as follow-ups for design, lab, and API fidelity.
