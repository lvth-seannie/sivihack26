# AI Career Navigator — Backend Spec

Status: draft · Owner: Backend (Hieu) · Audience: Frontend, Data Engineering

This document is the shared contract between the three workstreams. It is derived
from the **existing frontend code** (`frontend/src/services/api.js` and
`frontend/src/data/*.js`), which already defines exactly what the backend must
return. If the frontend contract and this document ever disagree, the frontend
code wins — update this document.

---

## 1. System overview

```
┌─────────────┐   HTTP / JSON   ┌────────────────────┐   SQL    ┌──────────────┐
│ React + Vite│ ──────────────► │ Django + Ninja API │ ───────► │ Supabase     │
│  (frontend) │ ◄────────────── │     (backend)      │ ◄─────── │ PostgreSQL   │
└─────────────┘                 └─────────┬──────────┘          └──────────────┘
                                          │ prompt + context
                                          ▼
                                   ┌────────────┐
                                   │ OpenAI API │
                                   └────────────┘
```

- The frontend makes **two** kinds of request (see §3).
- The backend owns all business logic: skill-gap calculation, market aggregation,
  and the OpenAI call.
- The `n8n` naming in the frontend is historical. There is **no n8n**. The
  Django endpoints replace it.

### Responsibility split

| Workstream | Owns |
|---|---|
| **Data Engineering** | Cleaning the raw datasets; creating and populating PostgreSQL tables; (ideally) SQL views for market aggregation; `backend/db/init.sql` |
| **Backend** | Django + Ninja API, schemas, skill-matching logic, roadmap builder, OpenAI wrapper, caching, deployment |
| **Frontend** | React UI (already built); setting `VITE_*` env vars to point at the deployed backend |

---

## 2. Environments and configuration

### Frontend env (`frontend/.env`)

| Var | Meaning | Local dev value |
|---|---|---|
| `VITE_MARKET_INSIGHTS_URL` | Full URL of the market-insights endpoint | `http://localhost:8000/api/market-insights` |
| `VITE_N8N_WEBHOOK_URL` | Full URL of the analysis endpoint | `http://localhost:8000/api/analyze` |

If either is unset, the frontend silently falls back to local mock data and shows
a "demo data" chip. Setting them switches to "Live backend".

### Backend env (`backend/.env` — **must be gitignored**)

| Var | Meaning |
|---|---|
| `DATABASE_URL` | Supabase Postgres connection string |
| `OPENAI_API_KEY` | OpenAI key. If absent, backend uses the deterministic fallback (no crash) |
| `DJANGO_SECRET_KEY` | Django secret (env-driven, not hardcoded) |
| `DJANGO_DEBUG` | `true` / `false` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames for the deployed backend |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins (e.g. `http://localhost:5173`, the Vercel URL) |

> **Action:** the current `backend/.env` with live Supabase credentials is
> committed to git. Rotate the DB password in Supabase, remove the file from
> tracking, and commit a `backend/.env.example` with empty values.

---

## 3. API contract

Base path: `/api`. All responses are JSON. Field names are **camelCase**.

The frontend normaliser (`api.js`) is lenient — it also accepts `snake_case` and a
few shape variants — but backend responses should match the canonical shape below
exactly and not rely on that leniency.

### 3.1 `GET /api/market-insights`

Powers the **Market Insights** page. Called once on app load.

**Request:** no params, no body.

**Response `200`:**

```jsonc
{
  "updatedAt": "2026-09-01",          // ISO date string, or null
  "topSkills": [
    { "name": "Python", "percentage": 44 },
    { "name": "SQL",    "percentage": 41 }
    // ~5 items, sorted desc by percentage
  ],
  "topRoles": [
    { "name": "Data Engineer", "percentage": 38 }
    // ~5 items
  ],
  "topLocations": [
    { "name": "Frankfurt", "percentage": 34 }
    // ~5 items
  ],
  "trends": [
    { "label": "AI / ML tooling demand", "percentage": 62, "direction": "up" }
    // direction: "up" | "down"
  ]
}
```

Notes:
- `name` and `percentage` keys are read directly by the UI — do not rename.
- `percentage` is an integer 0–100 (share of job postings that mention the item).
- `trends` has **no data source yet** (the dataset is a single snapshot with no
  time dimension). Options: (a) drop the card, (b) mark it illustrative, (c) get a
  second snapshot from Data Eng. Decide before the demo.
- This response should be **cached** (see §4.4).

### 3.2 `POST /api/analyze`

Powers the **AI Results** page. Called when the user clicks "Run AI Analysis".

**Request `body`:**

```jsonc
{
  "targetRole": "Data Engineer",                       // one of the known roles
  "currentSkills": ["Java", "Spring Boot", "SQL"]      // always a non-empty string array
}
```

The frontend already splits the comma-separated text field into an array and
validates that `targetRole` and at least one skill are present.

**Response `200`:**

```jsonc
{
  "matchScore": 67,                                    // integer 0–100
  "strengths": ["SQL", "Docker"],                      // string[] — required skills the user already has
  "missingSkills": ["Python", "Spark", "Airflow"],     // string[] — required skills the user lacks
  "roadmap": [
    {
      "phase": "Phase 1",
      "skill": "Python",
      "description": "Build working proficiency in Python through a focused project."
    }
    // one entry per missing skill, ordered by learning priority
  ],
  "recommendation": "You already cover 3 of 6 core skills for Data Engineer. Focus next on Python and Spark..."
}
```

Semantics:
- `matchScore = round(len(strengths) / len(requiredSkills) * 100)`.
- `strengths` + `missingSkills` together = the role's required skill set.
- `roadmap` is generated from `missingSkills`.
- `recommendation` is the only field that **requires** OpenAI. Everything else is
  computed deterministically.

**Errors:**

```jsonc
// 422 — validation
{ "detail": [ { "loc": ["body", "currentSkills"], "msg": "at least one skill required" } ] }

// 400 — unknown role
{ "detail": "Unknown targetRole 'Wizard'. Known roles: Data Analyst, Data Engineer, ..." }
```

### 3.3 `GET /api/roles`  *(new — recommended)*

Lets the frontend stop hardcoding the dropdown.

**Response `200`:**

```jsonc
{
  "roles": [
    { "id": "data-engineer", "label": "Data Engineer", "requiredSkills": ["Python", "SQL", "Spark", "Airflow", "AWS", "Docker"] }
  ]
}
```

Until this exists, the frontend list is the source of truth:
`Data Analyst`, `Data Engineer`, `Business Analyst`, `Software Engineer`, `Product Manager`.

### 3.4 `GET /api/health`  *(new — required for deploy)*

**Response `200`:** `{ "status": "ok" }`

---

## 4. Target backend architecture

### 4.1 Layout

```
backend/
├── core/                       # Django config only
│   ├── settings.py             # env-driven; SECRET_KEY / DEBUG / hosts / CORS from env
│   └── urls.py                 # mounts the Ninja API at /api/
├── api/                        # single Django app
│   ├── api.py                  # NinjaAPI() instance + router registration + exception handlers
│   ├── schemas.py              # Ninja/Pydantic schemas — mirror §3 exactly (camelCase)
│   ├── routers/
│   │   ├── market.py           # GET /market-insights, GET /roles
│   │   └── analysis.py         # POST /analyze
│   ├── services/               # business logic — no HTTP, no raw SQL
│   │   ├── skill_matching.py   # normalise, alias-map, diff, score   ← core algorithm
│   │   ├── market_insights.py  # shape aggregation results into the response
│   │   └── roadmap.py          # build roadmap[] from missingSkills
│   ├── repositories/           # all DB access
│   │   ├── jobs_repo.py        # queries over the job-market tables
│   │   └── applicants_repo.py  # queries over the Stack Overflow tables
│   ├── ai/
│   │   └── openai_client.py    # the ONLY module that imports `openai`; has a fallback
│   └── data/
│       └── role_skill_map.py   # curated role -> canonical required-skills mapping
├── db/
│   └── init.sql                # owned by Data Eng: DDL + seed
├── requirements.txt            # pinned
└── .env.example
```

Delete `backend/main.py` (mislabeled FastAPI stub). `backend/ai_module.py` becomes
`api/ai/openai_client.py`.

### 4.2 Principles

1. **Schemas mirror the frontend contract.** Write `schemas.py` straight from §3
   and the mock files. Emit camelCase (Ninja `Field(alias=...)` or model config).
2. **Deterministic core, AI narration only.** `matchScore`, `strengths`,
   `missingSkills`, `roadmap` skills are pure Python. OpenAI writes only
   `recommendation` and the roadmap `description` strings.
3. **AI always has a fallback.** No key / timeout / rate-limit → return a
   templated recommendation. Never 500 because of OpenAI.
4. **Don't fight Data Eng's schema with migrations.** Their tables are created by
   raw SQL. Use `class Meta: managed = False` models or a raw-SQL repository
   layer. Never run `makemigrations` against their tables.
5. **Sanitise `currentSkills` before it reaches the prompt** — cap count (e.g. 50)
   and length per skill (e.g. 60 chars), strip control chars. This is a
   prompt-injection surface.
6. **One `NinjaAPI` instance** at `/api/`, with exception handlers returning
   consistent JSON.

### 4.3 The skill-matching algorithm (most important part)

1. Determine the role's **required skills**:
   - Start from `role_skill_map.py` (hand-curated, reliable for the demo).
   - Optionally enrich from job data: for postings mapped to this role, parse
     `job_skills`, count frequency, take the top N.
2. **Normalise** both the required list and the user's list:
   - lowercase, trim, collapse whitespace
   - alias map: `js`→`javascript`, `postgres`/`postgresql`→`sql`, `py`→`python`,
     `react.js`→`react`, etc.
3. **Diff:** `strengths = required ∩ user`, `missingSkills = required − user`.
4. `matchScore = round(len(strengths) / len(required) * 100)`.
5. Return skills in their **canonical display form** (not the normalised form).

Unit-test this module hard — it is the product.

### 4.4 Caching

- `GET /api/market-insights`: cache the computed payload (Django cache framework
  or a module-level TTL cache), 1–24h TTL. Better: Data Eng exposes a SQL
  view / materialized view and the backend just `SELECT`s it.
- `POST /api/analyze`: optionally cache by `(targetRole, sorted(currentSkills))`
  to make repeated demo runs instant.

### 4.5 Database access notes

- `DATABASE_URL` currently points at the Supabase **transaction pooler** (port
  `6543`). Transaction pooling conflicts with Django persistent connections and
  server-side cursors. If you see connection errors: use the **session pooler**
  (port `5432`) for the backend, or set `conn_max_age=0`. Ensure `sslmode=require`.
- Keep Django's own tables (`auth`, `admin`, `sessions`) — they're harmless. Just
  don't migrate Data Eng's tables.

---

## 5. Data needed from Data Engineering

To unblock backend development, the backend needs:

1. **`backend/db/init.sql` populated** with real `CREATE TABLE` statements +
   seed data, so the API can be developed and demoed locally.
2. **Confirmed table + column names:**
   - ✅ Job market: `jobs(job_id, job_title, company, job_location, job_level,
     job_type)` + `job_skill(job_id, skill)` — one row per (job, skill).
     Backend codes against this now.
   - Candidates: `applicants(applicant_id, devtype, degree_clean, yearscodepro,
     country)`, `applicant_skill(applicant_id, skill)` — **only if in scope
     (see item 5).**
3. **A decision on `job_title` → role mapping.** Backend currently owns it
   (`role_skill_map.classify_title`, regex over free-text titles). A cleaned
   `role` column from Data Eng would be more reliable — optional.
4. **(Nice to have)** SQL aggregation views for the market-insights numbers
   (top skills / roles / locations by % of postings).
5. **A decision on the candidate dataset.** It is not used by any current screen.
   If it's in scope, define the feature (e.g. "you're ahead of X% of applicants
   for this role") so Backend can add an endpoint.

---

## 6. Build order (Backend)

### Phase 1 — Foundation (get real HTTP flowing) — ✅ DONE

- [x] Untrack `backend/.env`; add `backend/.env.example`; expand `.gitignore`.
      **⚠️ Still TODO by a human: rotate the Supabase DB password in the dashboard**
      — the old one is in git history.
- [x] Fill `requirements.txt` (pinned to installed versions). Standardised on
      **Django 6.1.1** (what the venv had). `openai==1.109.1` installed for Phase 3.
- [x] `startapp api`; `NinjaAPI()` mounted at `/api/`; `GET /api/health` live.
- [x] `api/schemas.py` written from §3 (camelCase fields).
- [x] `GET /api/market-insights`, `GET /api/roles`, `POST /api/analyze` all live,
      serving deterministic stub data from `api/stub_data.py`. `POST /api/analyze`
      already does real (case-insensitive) skill diffing against the curated role
      map — Phase 2 just swaps the data source.
- [x] CORS locked to `CORS_ALLOWED_ORIGINS` env (defaults to localhost:5173).
- [x] Settings made env-driven: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
      `DJANGO_ALLOWED_HOSTS`. Tests run on in-memory SQLite (no Supabase round-trip).
- [x] `api/tests.py`: 7 contract tests, all green (`python manage.py test api`).

**Frontend integration:** set in `frontend/.env`
```
VITE_MARKET_INSIGHTS_URL=http://localhost:8000/api/market-insights
VITE_N8N_WEBHOOK_URL=http://localhost:8000/api/analyze
```

### Phase 2 — Data + real logic — 🔨 IN PROGRESS

Data Eng confirmed the cleaned schema:
```
jobs(job_id, job_title, company, job_location, job_level, job_type)
job_skill(job_id, skill)          -- one row per (job, skill)
```

- [x] `api/repositories/jobs_repo.py` — raw SQL over `jobs` / `job_skill`
      (`managed = False`, no models). Every query is savepoint-wrapped and
      degrades to `[]` if the tables are absent (test DB).
- [x] `api/services/skills.py` — normalise + alias map (`js→javascript`,
      `postgres/mysql/…→sql`, `py→python`, …) + display-form lookup. Unit-tested.
- [x] `api/services/skill_matching.py` — `diff(required, current)` → strengths /
      missing / matchScore, alias-aware. `api/services/roadmap.py`,
      `api/services/recommendation.py` (the Phase 3 AI fallback).
- [x] `api/services/market_insights.py` — aggregates topSkills / topRoles
      (free-text titles bucketed via `role_skill_map.classify_title`) /
      topLocations, 1h in-process cache, **falls back to `stub_data` when the
      dataset is empty/unreachable** so the endpoint never 500s.
- [x] `api/data/role_skill_map.py` — curated map + title classifier +
      `role_catalogue()`. Optional data enrichment behind `ENRICH_FROM_DATA`
      (off by default). `GET /api/roles` served from here.
- [x] `POST /api/analyze` now deterministic on the real matcher; input capped
      (50 skills / 60 chars, control chars stripped) ahead of the Phase 3 prompt.
- [x] `api/tests.py`: 14 tests (contract + normalise/diff/roadmap/classify units).
- [ ] Point `DATABASE_URL` at the populated Supabase DB and eyeball
      `GET /api/market-insights` against real rows (tune the title/alias maps).
- [ ] Decide `trends` (currently returns `[]` from real data — no time dimension).
- [ ] Optional: SQL aggregation view from Data Eng instead of app-side grouping.

### Phase 3 — AI + production
- [ ] `openai_client.py`: JSON-mode structured output, gap context in the prompt,
      returns `recommendation` + roadmap descriptions. Deterministic fallback.
- [ ] Timeouts + response caching.
- [ ] Deployment: env-driven settings, gunicorn, Render config, static files;
      point `VITE_*` at the deployed URL.
- [ ] Tests: `skill_matching` unit tests + one contract test per endpoint.
- [ ] Pre-compute the 2–3 demo scenarios so they're instant and can't fail live.

---

## 7. Known risks

| Risk | Severity | Mitigation |
|---|---|---|
| Live DB credentials committed to git (`backend/.env`) | **Critical** | Rotate password now; untrack file; `.env.example` |
| `job_skills` parsing quality drives every match score | High | Invest in the alias map; unit-test `skill_matching` |
| UI roles don't map cleanly to dataset `job_title` values | High | Curated `role_skill_map.py` or cleaned `role` column from Data Eng |
| OpenAI latency / rate limits / cost during live demo | High | Deterministic core + templated fallback + pre-cached demo scenarios |
| `trends` card has no real data source | Medium | Drop it, relabel as illustrative, or get a second data snapshot |
| Supabase transaction pooler vs Django persistent connections | Medium | Session pooler (5432) or `conn_max_age=0`; `sslmode=require` |
| `CORS_ALLOW_ALL_ORIGINS=True`, hardcoded `SECRET_KEY`, `DEBUG=True` | Medium | Env-driven settings before deploy |
| Django version drift (4.2 in docs vs 6.1 installed) | Medium | Pick one; pin in `requirements.txt` |
| Monolithic `/analyze` may time out on Render free tier | Medium | Fast deterministic path + short AI timeout + fallback |
| Unbounded `currentSkills` flows into LLM prompt | Medium | Cap count/length; strip control chars |
| Candidate dataset has no feature or endpoint | Low | Team decision on scope |
| `main` branch empty; all work on feature branches | Low | Agree branch/merge strategy early |
