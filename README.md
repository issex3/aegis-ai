# Aegis AI

**Controlled adversarial security assessments for AI agents.**

Aegis is a full-stack product workspace for putting the agents you operate into industry sandboxes, attacking them with versioned scenarios, and keeping evidence you can re-run and compare. Built as a multi-tenant SaaS with encrypted credentials, organisation isolation, and a clear boundary between customer results and shared intelligence.

> Assessment results are internal evidence — not a certification, and not a claim that a live system is safe.

<p align="center">
  <img src="docs/images/hero.png" alt="Aegis landing page — hero and agent-under-test radar" width="920" />
</p>

<p align="center">
  <img src="docs/images/assessment.png" alt="Aegis simulated assessment record with findings and evidence" width="920" />
</p>

---

## Why this exists

AI agents get tools: refunds, invoices, patient records, CRM updates. Prompt changes, model upgrades, and new tools quietly reopen old weaknesses. Most teams still probe with one-off chats and screenshots.

Aegis turns that into a repeatable programme: connect an agent, profile what it can do, select scenarios, run against synthetic sandboxes, review findings with evidence, then baseline and retest.

---

## Product surfaces

| Area | What it demonstrates |
| --- | --- |
| **Landing + demo** | Product narrative, simulated assessment record, regression story |
| **Auth & orgs** | Registration, sessions, roles (owner / admin / analyst / viewer) |
| **Agent registry** | OpenAI-compatible endpoints + built-in demo agent; credentials encrypted at rest |
| **Simulation lab** | Six industry environments with role-gated synthetic tools |
| **Scenario library** | Versioned cases across industries and threat classes |
| **Assessments** | Runs, evidence, severity rules, PDF export |
| **Regression** | Baseline → rerun → compare by test ID |
| **Intelligence** | Separated dataset path; contribution only with explicit consent |

---

## Architecture

```text
Browser ──► Next.js (App Router) ──► FastAPI
                 │                      │
                 │ same-origin proxy    │ org-scoped authz
                 │ HttpOnly session     │ Fernet credentials
                 ▼                      ▼
              UI + RSC              Postgres / SQLite
                                    Celery + Redis (optional workers)
```

- The browser never talks to FastAPI directly in normal use.
- Sessions are random tokens stored as SHA-256 hashes in an HttpOnly cookie.
- Organisations are the isolation boundary for agents, assessments, findings, and reports.
- Outbound agent calls pass an SSRF guard (HTTPS/443, block private/metadata ranges, re-check DNS at connect).

---

## Tech stack

| Layer | Choices |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Motion, ECharts, TanStack Table/Virtual, CodeMirror |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic, Argon2id, Fernet, ReportLab |
| Data / jobs | SQLite (local) · PostgreSQL + Redis + Celery (compose) |
| Quality | pytest, Vitest, secret scan workflow |

---

## Quick start

**Requirements:** Python 3.11+, Node.js 22+

### 1. Environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy `.env.example` → `.env` at the repo root and set `ENCRYPTION_KEY` to the generated value.

### 2. API

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Docker

```powershell
# root .env required
docker compose up --build
```

---

## Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest

cd ..\frontend
npm test
```

---

## Repository layout

```text
backend/                 FastAPI, models, engine, sandboxes, scenarios, tests
frontend/                Next.js App Router product UI
security/                Policies, SOC2 notes, backup/restore helpers, secret scan
exports/                 Internal technical maturity write-up
docker-compose.yml       Local multi-service stack
.env.example             Safe template — never commit a real .env
```

---

## Security posture (high level)

- Passwords: Argon2id
- Agent API secrets: Fernet at rest; UI shows masked hints only
- Mutations require `X-Aegis-Client: web` (CSRF-style browser binding)
- Auth rate limiting, production boot checks, audit-oriented event trail
- Sandboxes use **fictional** data and simulated tools only
- Demo / simulated results are labelled as such

See `security/` for deeper policy and isolation notes.

---

## What this is not

- Not a compliance certification product
- Not a claim that Aegis itself has been independently penetration tested
- Not live attacks against real customer systems — sandboxes are synthetic

---

## License

MIT — see [LICENSE](LICENSE).
