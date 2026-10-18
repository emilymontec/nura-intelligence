<div align="center">

<!-- TODO: add logo -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme_assets/nura-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/readme_assets/nura-light.svg">
  <img alt="Nura Intelligence Logo" src="docs/readme_assets/nura-light.svg" width="300">
</picture>

<p align="center">
  <strong>Conversational Business Intelligence for e-commerce data — upload, ask, understand</strong>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#data-model">Data model</a> ·
  <a href="#analytics-engine">Analytics engine</a> ·
  <a href="#ai-chat--specialist-agents">AI agents</a> ·
  <a href="#api-reference">API</a> ·
  <a href="SETUP_DEPLOY_TESTING.md">Deploy</a>
</p>

<img src="https://img.shields.io/badge/backend-django%206-044b99?style=flat-square">
<img src="https://img.shields.io/badge/frontend-react%2019-dc4395?style=flat-square">
<img src="https://img.shields.io/badge/database-postgresql%2015-0697ac?style=flat-square">
<img src="https://img.shields.io/badge/queue-celery%20%2B%20redis-044b99?style=flat-square">
<img src="https://img.shields.io/badge/ML-scikit--learn-dc4395?style=flat-square">
<img src="https://img.shields.io/badge/license-apache%202.0-lightgrey?style=flat-square">

</div>

Most small e-commerce sellers and resellers have their sales data scattered across CSV/XLSX exports from **Temu**, **Shein** and **AliExpress**, and no realistic way to turn that into decisions — SQL is a barrier, "real" BI tools are built for analysts, and spreadsheets don't scale past a few hundred rows.

**Nura Intelligence removes that barrier.** You drop a file, the platform cleans and profiles it in the background, and from that point on you talk to your data the same way you'd talk to an analyst — in plain language, in a chat window — while the AI also looks for anomalies, correlations and risks on its own and surfaces them before you ask.

Everything below is backed by real code in this repository, not aspirational copy: every endpoint, model, agent and analytics function listed here exists in `services/`.

<!-- TODO: add product screenshot (chat + dashboard view) -->
![dashboard](docs/readme_assets/dashboard.jpeg)

---

## Why Nura

<div align="center">

| For sellers & resellers | For teams |
|---|---|
| Upload a marketplace export and get answers in minutes, no SQL. | Organizations, roles and shared workspaces — not a single-user toy. |
| The AI finds anomalies and trends you didn't think to ask about. | Comments, dataset/dashboard sharing, audit trail per action. |
| One click from a question to an exportable PDF/DOCX/PPTX report. | Triggers that react to new files, anomalies or dates automatically. |
| Dashboards you build yourself, or that the AI builds for you. | A documented public REST API (Swagger/Redoc) to integrate elsewhere. |
| "What-if" simulation on any numeric metric, no spreadsheet formulas. | Specialist agents per business area (finance, sales, marketing, ops). |

</div>

Nura isn't trying to be a general-purpose BI tool that happens to have a chatbot bolted on. It's built around one specific audience — people reselling or operating on Temu, Shein and AliExpress — and one specific workflow: export a file from the marketplace, drop it into Nura, and get the same kind of read a data analyst would give you, without hiring one.

---

## How a dataset moves through the platform

```
 Upload               Clean & profile          Analyze                 Converse
┌─────────┐          ┌─────────────────┐      ┌───────────────────┐   ┌────────────────────┐
│ CSV/XLSX│  ──────▶  │ header/lang/type │ ──▶  │ correlations       │──▶│ chat with context   │
│ /JSON   │  upload   │ detection, null  │      │ anomalies (IForest)│   │ (LLM router)         │
│         │           │ handling, dedup  │      │ KPIs, health score │   │ proactive insights   │
└─────────┘           └─────────────────┘      └───────────────────┘   └────────────────────┘
                                                        │                         │
                                                        ▼                         ▼
                                              ┌────────────────────┐   ┌────────────────────┐
                                              │ dashboards & charts │   │ PDF/DOCX/PPTX report │
                                              └────────────────────┘   └────────────────────┘
                                                        │
                                                        ▼
                                              ┌────────────────────┐
                                              │ triggers → notify /  │
                                              │ re-analyze / report  │
                                              └────────────────────┘
```

A file upload (synchronous for small files, a Celery task for large ones) runs through `services/analytics` for cleaning and statistical analysis, the result is persisted as a `Dataset` + `DatasetVersion`, and from there the chat (`services/ai`), dashboards, reports and triggers all read from the same analyzed dataset. Nothing downstream re-parses the raw file — everything works off the cleaned, versioned, already-profiled data.

---

## Quickstart

### 1. Clone & configure

```bash
git clone https://github.com/emilymontec/nura-intelligence.git
cd nura-intelligence
cp .env.example .env
```

### 2. Backend (Django)

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

If `DATABASE_URL` is empty, the project falls back to **SQLite** automatically — no local Postgres needed to try it out. Same pattern for `REDIS_URL`: leave it empty and Celery tasks run synchronously in-process instead of needing a broker, and the cache falls back to an in-process memory cache instead of Redis.

### 3. Frontend (React + Vite), in another terminal

```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

Open **http://localhost:5173** — that's the app. `http://localhost:8000` is only the backend API (you'll see a status JSON, not the UI, if you open it directly).

### 4. Give the chat something to talk to

The AI chat needs at least one LLM provider key in `.env`: `GROQ_API_KEY`, `CEREBRAS_API_KEY` or `OPENROUTER_API_KEY`. Without one, everything else (auth, uploads, dashboards, analytics) still works — only the chat endpoint returns an error. The router (`services/ai/llm.py`) tries providers in order and falls back automatically if one is rate-limited or unavailable, so configuring more than one key makes the chat noticeably more reliable in practice.

### 5. Generate a realistic sample dataset

```bash
python scripts/generar_dataset_ejemplo.py
```

200 rows of synthetic Temu/Shein/AliExpress orders — deliberately imperfect, with nulls in `calificacion_cliente`/`dias_entrega`, two price outliers and a duplicate row, so the analytics engine (anomaly detection, data health score, correlations) has something real to find the first time you upload a file. Pass `--out` and `--filas` to generate a different size or path.

### 6. Or run everything with Docker

```bash
cd docker
docker compose up --build
```

Spins up Postgres, Redis, the Django service, a Celery worker, an Nginx gateway and the frontend dev server, each with health checks. Full guide — env vars, production deployment, logging/monitoring, CI — in [SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md).

---

## Screenshots

<!-- TODO: replace every placeholder below with a real capture at docs/readme_assets/ -->

<table>
<tr>
<td width="50%" valign="top">

**Chat with context**
![Chat view](docs/readme_assets/chat_view.jpeg)

</td>
<td width="50%" valign="top">

**Dashboard builder**
![Dashboard builder](docs/readme_assets/dashboard_builder.jpeg)

</td>
</tr>
<tr>
<td width="50%" valign="top">

**File manager / workspace**
![File manager](docs/readme_assets/file_manager.jpeg)

</td>
<td width="50%" valign="top">

**Anomaly & insight feed**
![Insight feed](docs/readme_assets/insight_feed.jpeg)

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Exported PDF report**
![Report export](docs/readme_assets/report_export.jpeg)

</td>
<td width="50%" valign="top">

**Organization & members**
![Organization settings](docs/readme_assets/organization_settings.jpeg)

</td>
</tr>
</table>

---

## Architecture

Nura runs as a small set of cooperating services rather than a single monolith process, even though the backend logic lives in one Django codebase. In Docker (`docker/docker-compose.yml`) these are the moving parts:

```
                         ┌─────────────────┐
                         │     Gateway      │   nginx — reverse proxy,
                         │     (nginx)      │   serves collected static files
                         └────────┬─────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                  ▼
        ┌─────────────────┐               ┌──────────────────┐
        │  chat-service    │               │     frontend      │
        │  (Django + DRF)  │               │  (React + Vite)   │
        │  REST API, auth, │               │  dev server, or    │
        │  analytics, chat │               │  static build      │
        └────────┬─────────┘               └──────────────────┘
                  │
       ┌──────────┼──────────────┐
       ▼          ▼              ▼
┌────────────┐ ┌───────┐  ┌──────────────┐
│ postgres-   │ │ redis │  │ celery-worker │
│ chat        │ │       │  │ (async        │
│ (Postgres   │ │ broker│  │  analysis)    │
│  15)        │ │+cache │  │               │
└────────────┘ └───────┘  └──────────────┘
```

| Service | Role |
|---|---|
| `chat-service` | The Django app — REST API, auth, workspace, datasets, chat, dashboards, triggers, sharing. Everything under `services/chat`, `services/ai`, `services/analytics` runs inside this one process. |
| `celery-worker` | Same codebase, run as a worker instead of a web server (`celery -A nura worker`). Picks up large-file analysis, scheduled trigger checks and report generation so the request/response cycle never blocks on them. |
| `postgres-chat` | Primary datastore. Falls back to SQLite automatically when `DATABASE_URL` is unset, so the whole stack can run without it in local development. |
| `redis` | Celery broker/result backend and, when configured, the Django cache backend. Falls back to synchronous (eager) task execution and an in-process cache when unset. |
| `gateway` (nginx) | Reverse proxy in front of `chat-service`; also serves collected static files (`/static/`) in the containerized setup. |
| `frontend` | React + Vite app. Runs as a dev server in Docker Compose; in production it's built to static files and served separately (see [SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md)). |

This is intentionally a **modular monolith with a separable worker**, not a sprawling microservice mesh: the domain logic for data, chat and analytics is organized into distinct Python packages (`services/chat`, `services/ai`, `services/analytics`) with clear boundaries, which keeps a single deploy simple while leaving a clean seam to split any of them into its own service later if scale ever demands it.

---

## Data model

The core domain, as defined in `services/chat/models.py`:

<table>
<tr>
<td width="50%" valign="top">

**Workspace & identity**
- `Organization` / `Membership` — multi-tenant orgs with roles (owner, admin, member)
- `Workspace` — one auto-provisioned space per user, created on first login
- `UserProfile` — MFA secret, notification and display preferences

**Data**
- `Dataset` / `DatasetVersion` — the uploaded file, cleaned, profiled and versioned on every change
- `FileCategory` / `DatasetTag` — folders and labels for organizing a workspace at scale

</td>
<td width="50%" valign="top">

**Conversation & output**
- `ChatSession` / `ChatMessage` — one thread per conversation, with rolling memory across messages
- `Dashboard` — manual or AI-generated, built from one or more analyzed datasets
- `Recommendation` — proactive, AI-authored suggestions tied to a dataset, with a dismiss state

**Collaboration**
- `SharedAccess` / `Comment` — sharing datasets/dashboards with specific users, threaded discussion
- `Trigger` / `TriggerLog` — automation rules (event → action) and their full run history, for auditing

</td>
</tr>
</table>

Every relationship is scoped to a workspace or organization: a `Dataset` belongs to exactly one `Workspace`, access to it is checked per-user even when it's been shared (`_user_can_access_dataset`), and nothing in the chat or analytics layer ever reads across workspace boundaries.

---

## Data engine

Everything a raw file goes through before it becomes something you can chat with — implemented in `services/analytics/cleaning.py` and `analyzer.py`:

| Step | What it does |
|---|---|
| **Format detection** | Accepts CSV, XLSX and JSON; detects delimiter, encoding and header row automatically (`detect_headers`, `_is_valid_header_row`). |
| **Language & type detection** | Infers column language and semantic type per column — numeric, date, categorical, currency (`detect_language`, `_infer_semantic_type`). |
| **Number & date normalization** | Handles mixed decimal separators, currency symbols and date formats across locales (`normalize_numbers`, `normalize_dates`, `_try_parse_dates`). |
| **Null handling & deduplication** | `handle_nulls`, `remove_duplicates`, `normalize_whitespace` — the dataset that reaches the analytics layer is clean, not just a raw copy with a schema attached. |
| **Industry detection** | Infers the likely business context (e.g. e-commerce) from the column set, to steer how the AI frames its answers (`detect_industry`, `get_business_context`). |
| **Versioning** | Every re-analysis, merge or restore creates a new `DatasetVersion` — nothing about the pipeline is destructive, and any previous version can be restored. |

The pipeline is deliberately defensive: it's built to turn a messy, inconsistent marketplace export into something structurally sound, rather than assuming the input is already a tidy CSV. The bundled sample generator (`scripts/generar_dataset_ejemplo.py`) exists specifically to exercise this — it injects nulls, outliers and a duplicate row on purpose, so a first upload has something real for the pipeline to catch.

---

## Analytics engine

Runs automatically on every analyzed dataset (`services/analytics/`), independent of whether anyone asks a question:

<table>
<tr>
<td width="33%" valign="top">

**Statistics**

- Column-level stats (`calculate_basic_stats`)
- Correlation matrix above a configurable threshold (`compute_correlations`)
- Trend direction per numeric column (`analyze_numeric_trends`, `compute_trend`)
- Simple forecasting (`simple_forecast`)

</td>
<td width="33%" valign="top">

**Anomalies & risk**

- **Isolation Forest** outlier detection (`detect_anomalies`)
- Fraud/inconsistency signal checks (`check_fraud_signals`)
- Critical-variable detection (`detect_critical_variables`)
- Overall **data health score** (`health_score`, `risk_level`)

</td>
<td width="33%" valign="top">

**Insights**

- Auto-generated KPI cards (`get_kpis`)
- Plain-language explanation of what drives the data (`explain_importance`)
- Proactive insight feed, independent of chat (`generate_insight_feed`)
- "What-if" scenario simulation on any numeric target (`what_if_simulation`)

</td>
</tr>
</table>

This is the part of the spec that matters most: **the AI doesn't only answer — it also looks.** `generate_insight_feed` and `generate_ai_cards` run after every upload and populate the dashboard with findings nobody had to ask for — a drop in average rating for one platform, a price outlier that doesn't match the rest of a category, a correlation between delivery time and cancellation rate. The chat is one way to reach this layer; it is not the only way data gets analyzed.

---

## AI chat & specialist agents

The chat (`services/ai/`) keeps context of the active dataset *and* the conversation history (`MemoryManager` in `services/chat/views.py`), and routes each question through an intent classifier (`route_intent`) before answering — so a question like "what's my best-selling category" is handled differently from "what should I do about these cancellations."

### LLM routing

`LLMRouter` (`services/ai/llm.py`) is provider-agnostic: it's configured with whichever of `GROQ_API_KEY`, `CEREBRAS_API_KEY` or `OPENROUTER_API_KEY` are present, tries them in order, and falls back to the next provider on a rate limit or failure instead of surfacing an error to the user. Requests are tiered (`tier="standard"` vs. a lighter tier for cheap classification calls like intent routing) so the expensive model is only used where the answer quality actually benefits from it.

### Specialist agents

For deeper questions, the router can fan a question out across **specialized agents by business area** (`services/ai/agents.py`) and synthesize their answers:

| Agent | Business area | Focus |
|---|---|---|
| Memory Assistant | general | Recalls earlier parts of the conversation or older files for continuity |
| Alert Detector | finance | Anomalies, missing data, early warning signs |
| Opportunity Explorer | sales | Patterns and what's working well |
| Strategic Advisor | marketing | Concrete next steps and recommendations |
| Business Vision | general | Executive summary — the money/time impact |
| Operations Manager | operations | Day-to-day process efficiency |
| Future Guide | finance | Forecasts and trend projection |

Agents run in parallel (`ThreadPoolExecutor`, `run_agent_team`) when a question needs more than one perspective, then a synthesis pass merges their answers into a single, coherent response rather than five pasted opinions. The `agents/by-area/` endpoint also exposes this directly, so the frontend can let a user pick "ask my finance agent" explicitly instead of relying on automatic routing.

### Example

```
You: Why did AliExpress orders drop in the last two weeks?

Nura: AliExpress order volume is down 23% week-over-week, concentrated
in the "Electrónica" and "Herramientas" categories. Average delivery
time for AliExpress orders in that window is 29 days — about 9 days
above your 90-day average — which lines up with a rise in "Cancelado"
status for the same period. Shein and Temu show no equivalent delivery
slowdown. This looks like a fulfillment issue on AliExpress's side
rather than a demand problem on yours.
```

---

## Dashboards & reports

- **Charts**: bar, line, pie, heatmap, scatter (`ChartExportButtons`, `HeatmapChart` in the frontend), exportable to PNG/SVG.
- **Dashboards**: build one manually (`DashboardBuilder`) or generate one with AI (`dashboard_generate_ai`), from any analyzed dataset — the AI picks the chart types and metrics it judges most relevant rather than defaulting to a fixed template.
- **Reports**: export a full chat session as a formatted report — `export_session_report_pdf`, `_docx`, `_pptx` — with executive, technical or financial framing, so the same conversation can become a one-page summary for a stakeholder or a detailed appendix for an analyst.

<!-- TODO: add dashboard screenshot -->
![Smart Dashboard](docs/readme_assets/smart_dashboard.jpeg)

---

## Automation (triggers)

`Trigger` + `TriggerLog` implement event → action automation, checked on a schedule (`trigger_check_scheduled`) and logged for auditing:

| Trigger | Action |
|---|---|
| New file uploaded to a watched category | Auto-analyze and notify |
| Anomaly detected above a threshold | Notify / generate a report |
| Scheduled date reached | Re-analyze and send a report |

Every run — whether it fired, what it did, and whether it succeeded — is written to `TriggerLog`, so a trigger's behavior over time is auditable rather than a black box. In production, `trigger_check_scheduled` is meant to run periodically via Celery beat or an external scheduler; see [SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md) for wiring that up.

---

## Collaboration & multi-tenancy

- **Organizations & roles** — `Organization`, `Membership`, with role-gated endpoints (`_get_membership_or_403`): owners and admins can manage members, regular members operate within their own access.
- **Sharing** — datasets and dashboards can be shared with specific users (`SharedAccess`, `share_create`/`share_revoke`), surfaced via "shared with me" endpoints (`shared_datasets_list`, `shared_dashboards_list`).
- **Comments** — threaded discussion on a dataset or dashboard (`Comment`), so a finding doesn't have to leave the platform to be discussed.
- **MFA** — TOTP-based two-factor auth, enforced on login when enabled (`mfa_setup`/`mfa_enable`/`mfa_verify_login`, `pyotp`), with a custom login view (`custom_login_view`) that requests the second factor before issuing tokens.

---

## Security

- JWT authentication (SimpleJWT) with refresh-token rotation and blacklisting on logout.
- Password reset, email verification and registration via `dj-rest-auth` + `django-allauth`.
- Optional TOTP MFA on login, enforced per-user rather than platform-wide.
- Role-based access on organization resources; dataset/dashboard access checked per-user even when shared (`_user_can_access_dataset`, `_user_can_access_dashboard`) — a share grants access to one user, not to anyone who guesses the URL.
- `drf-spectacular` publishes the full API schema, so every endpoint's auth requirements are explicit, reviewable and kept in sync with the actual code rather than hand-maintained documentation.
- Secrets (Django secret key, LLM provider keys, database credentials) are read exclusively from environment variables — nothing sensitive is committed to the repository, and `.env.example` documents every variable without real values.

---

## Tech stack

<img src="https://img.shields.io/badge/Django-6.0-044b99?style=flat-square"> <img src="https://img.shields.io/badge/DRF-3.17-dc4395?style=flat-square"> <img src="https://img.shields.io/badge/SimpleJWT-5.5-0697ac?style=flat-square"> <img src="https://img.shields.io/badge/Celery-5.4-044b99?style=flat-square"> <img src="https://img.shields.io/badge/Redis-5.2-dc4395?style=flat-square"> <img src="https://img.shields.io/badge/Pandas-3.0-0697ac?style=flat-square"> <img src="https://img.shields.io/badge/NumPy-2.4-044b99?style=flat-square"> <img src="https://img.shields.io/badge/ScikitLearn-1.8-dc4395?style=flat-square"> <img src="https://img.shields.io/badge/React-19-0697ac?style=flat-square"> <img src="https://img.shields.io/badge/Vite-8-044b99?style=flat-square"> <img src="https://img.shields.io/badge/TailwindCSS-4-dc4395?style=flat-square"> <img src="https://img.shields.io/badge/ChartJS-4-0697ac?style=flat-square"> <img src="https://img.shields.io/badge/PostgreSQL-15-044b99?style=flat-square"> <img src="https://img.shields.io/badge/Sentry-optional-dc4395?style=flat-square">

**Backend**: Django 6, Django REST Framework, SimpleJWT, `dj-rest-auth` + `django-allauth` for registration/password flows, `drf-spectacular` for the OpenAPI schema and Swagger/Redoc UIs, Celery for async work, `pandas`/`numpy`/`scikit-learn`/`scipy` for the analytics and anomaly-detection layer, `reportlab`/`python-docx`/`python-pptx`-style export for reports.

**Frontend**: React 19, Vite, Tailwind CSS 4, Chart.js (`react-chartjs-2`), `react-markdown` + `remark-gfm` for rendering the chat's formatted answers, `react-router-dom` for client-side routing, `lucide-react` for icons.

**Infrastructure**: Docker, Docker Compose, GitHub Actions CI (backend tests against real Postgres/Redis + frontend build), structured logging to stdout, optional Sentry monitoring, a `/healthz/` health check endpoint used by the Docker healthchecks and suitable for any external load balancer or orchestrator.

**Storage**: local disk by default (`FileSystemStorage`), or Supabase's S3-compatible object storage when `SUPABASE_*` variables are set — same pattern as the database and cache: a working local fallback with an explicit opt-in to the production-grade backend.

---

## Project layout

```
nura-intelligence/
│
├── nura/                    # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── health.py            # /healthz/ — checks DB + cache
│   └── status_view.py       # / — API status page
│
├── services/
│   ├── chat/                 # accounts, workspace, datasets, dashboards,
│   │                          # triggers, sharing, comments, reports (models,
│   │                          # views, serializers, tests)
│   ├── ai/                   # LLM router, specialist agents, prompts
│   └── analytics/             # cleaning, anomalies, trends, scoring,
│                                forecasting, insights
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── auth/         # login, register, password reset, MFA
│       │   ├── chat/         # chat UI
│       │   ├── dashboard/    # file manager, dashboard builder, metrics
│       │   ├── analytics/    # charts, heatmaps, export buttons
│       │   └── landing/      # public marketing pages
│       ├── contexts/
│       ├── styles/
│       └── utils/
│
├── docker/
│   ├── docker-compose.yml    # postgres + redis + django + celery worker + nginx + frontend
│   └── nginx/
│
├── scripts/
│   └── generar_dataset_ejemplo.py
│
├── shared/
│   └── nura-shared/          # shared internal package
│
├── manage.py
├── requirements.txt
├── pytest.ini
├── .env.example
└── SETUP_DEPLOY_TESTING.md
```

---

## Frontend

The React app under `frontend/src/` is organized by feature rather than by file type, so a change to "how sharing works" touches one directory instead of three:

| Area | What lives there |
|---|---|
| `components/auth/` | Login, registration, password reset and MFA setup/verification screens. |
| `components/chat/` | The conversational UI — message list, markdown rendering, session switching, report export buttons. |
| `components/dashboard/` | File manager (upload, rename, move, tag, star, archive), dashboard builder, KPI/metric cards. |
| `components/analytics/` | Chart components (bar/line/pie/heatmap/scatter) and the PNG/SVG export controls. |
| `components/landing/` | Public, unauthenticated marketing pages. |
| `contexts/` | Shared React context — auth state, active workspace/dataset. |

The frontend talks to the backend purely over the REST API documented below; there's no server-side rendering or coupling to Django's templating beyond the account email templates under `nura/templates/account/`.

---

## API reference

With the backend running:

- `http://localhost:8000/api/docs/` — Swagger UI
- `http://localhost:8000/api/redoc/` — Redoc
- `http://localhost:8000/healthz/` — health check (DB + cache, used by Docker/orchestrators)
- `http://localhost:8000/` — plain-JSON API status page

Endpoints are grouped by domain under `services/chat/urls.py`:

| Group | Examples |
|---|---|
| `datasets/*` | upload, versioning, merge, explore, preview, columns, statistics, search, filter, what-if, tags, bulk-delete, duplicate, archive, reanalyze, download, import from URL/GraphQL/DB |
| `dashboards/*` | list/create, AI-generate, detail |
| `triggers/*` | list/create, detail, scheduled check |
| `organizations/*` | list/create, detail, members |
| `shares/*` | create, revoke, shared-with-me for datasets and dashboards |
| `comments/*` | create, delete |
| `agents/by-area/` | ask a specific specialist agent directly |
| `recommendations/*` | list, dismiss, generate for a dataset |
| `auth/*` | login (with MFA), registration, password reset, MFA setup/enable/disable |
| `chat/*`, `sessions/*` | ask a question, list/rename/delete sessions, export a session as PDF/DOCX/PPTX |

<!-- TODO: add API docs screenshot -->
![API docs](docs/readme_assets/api_docs.jpeg)

---

## Testing & CI

```bash
python manage.py test chat --verbosity=2
```

Tests live under `services/chat/tests/` and cover the domain models and the views layered on top of them. Every push and pull request against `main` runs the backend suite against **real** Postgres and Redis services (not the local SQLite/eager-mode fallback), verifies `/healthz/` responds, and builds the frontend. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — don't delete the test suite or this workflow; they're what keeps future changes from silently breaking a module that already works.

```bash
# frontend build check (same as CI)
cd frontend && pnpm run build
```

---

## Configuration reference

All variables are documented inline in [`.env.example`](.env.example).

| Variable | Required? | Fallback if empty |
|---|---|---|
| `DJANGO_SECRET_KEY` | production only | insecure dev key |
| `DJANGO_DEBUG` | no | `True` |
| `DJANGO_ALLOWED_HOSTS` | production only | `*` |
| `DATABASE_URL` | no | SQLite |
| `REDIS_URL` | no | Celery runs tasks synchronously, cache falls back to in-memory |
| `FRONTEND_URL` | no | `http://localhost:5173` |
| `GROQ_API_KEY` / `CEREBRAS_API_KEY` / `OPENROUTER_API_KEY` | at least one, for chat | chat endpoint returns an error |
| `DEFAULT_FROM_EMAIL` / `MAILGUN_DOMAIN` | no | console email backend (prints to stdout) |
| `SUPABASE_PROJECT_ID` / `SUPABASE_ACCESS_KEY_ID` / `SUPABASE_SECRET_ACCESS_KEY` / `SUPABASE_BUCKET_NAME` | no | files stored on local disk instead of S3-compatible storage |
| `DJANGO_LOG_LEVEL` | no | `DEBUG` in dev, `INFO` in production |
| `SENTRY_DSN` | no | no error reporting, console logging only |
| `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE` | no | `development`/`production` by `DEBUG`, `0.0` |

---

## Deployment

The project is designed around the same fallback pattern at every layer — database, cache/broker, storage, error reporting — so the same codebase runs unmodified from "nothing configured, SQLite and local disk" up to "Postgres, Redis, Supabase storage and Sentry." Moving from one to the other is a matter of setting environment variables, not changing code.

For a step-by-step production deployment — reverse proxy configuration, collecting static files, running migrations safely, wiring up a process manager for the Celery worker and beat schedule, and enabling Sentry — see [SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md).

---

## Known limitations

- Scheduled triggers rely on `trigger_check_scheduled` being invoked periodically (Celery beat or an external cron); there's no built-in scheduler process started automatically.
- External database import (`dataset_import_db`) exists as an endpoint but has no dedicated frontend UI yet — it's reachable via the API only.
- There's no per-organization API rate limiting yet; the public API is authenticated but not throttled.
- Frontend has no automated test suite (unit or e2e) — only a production build is checked in CI.
- The chat is only as good as the configured LLM provider; with no key set, every other module (auth, uploads, dashboards, analytics, reports) still works normally.

---

## FAQ

**Does it work without Postgres or Redis installed locally?**
Yes — that's the default. `DATABASE_URL` unset means SQLite; `REDIS_URL` unset means Celery runs tasks synchronously and the cache is in-process memory. Docker Compose is for running the production-shaped stack, not a requirement for local development.

**Which LLM providers are supported?**
Groq, Cerebras and OpenRouter, selected by whichever `_API_KEY` variables are present. The router tries them in order and falls back automatically; nothing in the code is tied to a single provider.

**What file formats can I upload?**
CSV, XLSX and JSON. Format, delimiter, encoding and header row are detected automatically.

**Can more than one person use the same dataset?**
Yes, through organizations and the sharing endpoints (`SharedAccess`) — a dataset or dashboard can be shared with specific users, who then see it under "shared with me."

**Is the sample data real?**
No — `scripts/generar_dataset_ejemplo.py` generates synthetic Temu/Shein/AliExpress orders with deliberate imperfections (nulls, outliers, a duplicate row) specifically to exercise the data-cleaning and anomaly-detection pipeline.

---

## Roadmap

- [ ] External database connectors beyond manual import (`dataset_import_db` exists; UI for scheduled sync is pending).
- [ ] Google Drive / Dropbox ingestion triggers.
- [ ] SSO (beyond the current email/MFA auth).
- [ ] Public API rate limiting per organization.
- [ ] Automated frontend test suite (unit and/or end-to-end).
- [ ] Built-in scheduler process for trigger checks, instead of relying on an external cron.

---

## Contributing

```bash
git checkout -b feature/my-feature
git commit -m "Add new feature"
git push origin feature/my-feature
```

Open a Pull Request describing the proposed changes. Backend changes should keep `python manage.py test chat` green; frontend changes should keep `pnpm run build` green — both are enforced by CI.

---

## Author

**Emily Monterrosa Castro — Full Stack Developer** <br>
[GitHub](https://github.com/emilymontec) · [LinkedIn](https://www.linkedin.com/in/emilymontec/) · [Portfolio](https://emilymontec.github.io/portfolio/)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <strong>Upload your data. Ask in plain language. Get answers.</strong>
</p>