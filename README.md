<p align="center">
  <!-- TODO: add logo -->
  <!--
  <picture>
    <source srcset="frontend/public/logo-dark.svg" media="(prefers-color-scheme: dark)">
    <source srcset="frontend/public/logo-light.svg" media="(prefers-color-scheme: light)">
    <img src="frontend/public/logo-light.svg" alt="Nura Intelligence" width="400" />
  </picture>
  -->
  <img src="https://via.placeholder.com/400x120?text=Nura+Intelligence" alt="Nura Intelligence" width="400" />
</p>

<p align="center">
  <strong>Conversational Business Intelligence for e-commerce data. Upload a dataset, ask questions in plain language, get answers, charts and reports.</strong>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#modules">Modules</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="SETUP_DEPLOY_TESTING.md">Setup &amp; Deploy</a> ·
  <a href="#api-reference">API</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13-blue?style=flat-square" alt="python" />
  <img src="https://img.shields.io/badge/django-6.0-success?style=flat-square" alt="django" />
  <img src="https://img.shields.io/badge/react-19-61DAFB?style=flat-square" alt="react" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-lightgrey?style=flat-square" alt="license" />
</p>

---

Nura Intelligence is a conversational Business Intelligence platform. You upload a dataset (CSV, XLSX or JSON), the platform cleans it, profiles it and hands it to an AI engine that can be asked questions in natural language — and it also looks for things in the data on its own, without being asked.

It ships with a working example built around three e-commerce marketplaces — **Temu**, **Shein** and **AliExpress** — but the data engine, chat and analytics layers are domain-agnostic: any tabular dataset works.

<!-- TODO: add product screenshot (chat + dashboard view) -->
<p align="center">
  <img src="https://via.placeholder.com/1400x820?text=Chat+%2B+Dashboard+screenshot" alt="Nura Intelligence product screenshot" width="100%" />
</p>

| | |
|---|---|
| 💬 **Conversational analytics** | Chat with your dataset — ask for trends, comparisons, breakdowns — with full context of the active dataset and conversation history. |
| 🧹 **Automatic data engine** | Format detection, null handling, type inference, deduplication. Raw files become clean, versioned internal datasets. |
| 🔎 **Proactive insights** | Correlations, distributions, anomaly detection (Isolation Forest) and auto-computed KPIs — surfaced without being asked. |
| 📊 **Visualizations & dashboards** | Bar, line, pie, heatmap and scatter charts, exportable to PNG/SVG/PDF. Build dashboards manually or let the AI generate them. |
| 📄 **Automated reports** | Executive, technical and financial reports, exportable to PDF/DOCX/PPTX. |
| ⚡ **Automation & triggers** | New file, detected anomaly or scheduled date → automatically analyze, notify or generate a report. |
| 🧑‍🤝‍🧑 **Collaboration** | Organizations, roles, sharing and comments on top of a multiuser workspace model. |
| 🏢 **Enterprise AI** | Specialized agents per business area (finance, sales, marketing), "what-if" simulations and proactive recommendations. |

---

## Use Nura Intelligence

<table>
<tr>
<td width="50%" valign="top">

<h3>📈 I want to analyze my data</h3>

Upload a CSV/XLSX/JSON file, let the data engine clean and profile it, then just ask questions in natural language.

**[→ Jump to Quickstart](#quickstart)**

</td>
<td width="50%" valign="top">

<h3>🔧 I'm extending the platform</h3>

Each module is an independent Django app/service under `services/`, with its own models, tests and (where it applies) Celery tasks.

**[→ Jump to Architecture](#architecture)**

</td>
</tr>
<tr>
<td colspan="2" valign="top">

<h3>🚀 I want to deploy it</h3>

Docker Compose setup with Postgres, Redis, Celery workers and an Nginx-served frontend. Full guide, including CI/CD, logging and monitoring:

**[→ SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md)**

</td>
</tr>
</table>

---

## Quickstart

### 1. Backend (Django)

```bash
cp .env.example .env
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

If `DATABASE_URL` is not set in `.env`, the project falls back to **SQLite** automatically — no local Postgres required to try it out.

### 2. Frontend (React + Vite), in another terminal

```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

### 3. Open the app

👉 **http://localhost:5173** is the user interface.

`http://localhost:8000` is only the backend API (you'll see a status page, not the app).

### AI chat

The conversational engine needs at least one LLM provider key in `.env` (`GROQ_API_KEY`, `CEREBRAS_API_KEY` or `OPENROUTER_API_KEY`). Without one, the rest of the platform (auth, dataset upload, etc.) still works, but the chat will return an error.

### Try it with sample data

```bash
python scripts/generar_dataset_ejemplo.py
```

Generates a realistic 200-row e-commerce dataset (Temu/Shein/AliExpress orders), deliberately imperfect — nulls, a couple of price outliers and a duplicate row — so there's something real for the analytics engine to detect end to end.

### Run with Docker

```bash
cd docker
docker compose up --build
```

See [SETUP_DEPLOY_TESTING.md](SETUP_DEPLOY_TESTING.md) for the full Docker, environment variable and production deployment guide.

---

## Modules

<!-- TODO: add architecture / module diagram -->
<p align="center">
  <img src="https://via.placeholder.com/1000x500?text=Module+diagram" alt="Module diagram" width="80%" />
</p>

| # | Module | What it does |
|---|--------|---------------|
| 1 | **Accounts & Workspace** | Full auth (register, login, password recovery, profile), an auto-provisioned workspace per user, and file upload/management (CSV, XLSX, JSON) with validation and metadata. |
| 2 | **Data Engine** | Automatic reading and cleaning (format detection, nulls, types, duplicates), file → internal dataset conversion, and dataset CRUD: versioning, merging, exploration, basic statistics. |
| 3 | **Conversational AI + Analytics** | Chat with context of the active dataset and conversation history; analytical engine for correlations, distributions, anomalies and automatic KPIs. The AI also surfaces findings proactively. |
| 4 | **Visualization & Reports** | Charts (bar, line, pie, heatmap, scatter) exportable to PNG/SVG/PDF; buildable dashboards (manual or AI-generated); automated executive/technical/financial reports exportable to PDF/DOCX/PPTX. |
| 5 | **Automation & Collaboration** | Triggers (new file, anomaly, date) → actions (analyze, notify, generate report); multiuser model with organizations, roles, sharing and comments; external integrations (databases, Drive/Dropbox, REST/GraphQL APIs). |
| 6 | **Enterprise AI** | Specialized agents per business area (finance, sales, marketing), "what-if" simulations and proactive recommendations, multi-company support, SSO/MFA, a public API, and scalability via microservices, caching and load balancing. |

---

## Architecture

```
nura-intelligence/
├── docker/          # docker-compose, Nginx config, Dockerfiles
├── frontend/         # React + Vite + TypeScript + Tailwind SPA
├── nura/              # Django project config (settings, urls, celery app)
├── services/
│   ├── chat/          # Module 1, 3 (chat), 4, 5, 6 — Django app: models, views, tasks
│   ├── ai/             # LLM integration, agents, prompts
│   └── analytics/       # Module 2, 3 (analytics) — cleaning, anomalies, trends, scoring
└── scripts/              # utility & sample-data scripts
```

### Infrastructure
Docker · Docker Compose · environment variables · GitHub Actions CI/CD · structured logging · Sentry monitoring (optional) · Django/pytest test suite

### Backend
Django 6 · Django REST Framework · JWT auth (SimpleJWT + dj-rest-auth + allauth) · Celery · Redis · PostgreSQL (SQLite fallback for local dev) · pandas / scikit-learn for the analytics engine · drf-spectacular for the public API schema

### Frontend
React 19 · Vite · Tailwind CSS · Chart.js

<!-- TODO: add tech stack diagram or logos row -->
<p align="center">
  <img src="https://via.placeholder.com/900x160?text=Tech+stack+logos" alt="Tech stack" width="70%" />
</p>

---

## API reference

With the backend running, interactive API docs are available at:

- `http://localhost:8000/api/schema/swagger-ui/` — Swagger UI
- `http://localhost:8000/api/schema/redoc/` — Redoc
- `http://localhost:8000/healthz/` — health check (DB + cache)

<!-- TODO: add API docs screenshot -->
<p align="center">
  <img src="https://via.placeholder.com/1200x700?text=Swagger+UI+screenshot" alt="API docs screenshot" width="100%" />
</p>

---

## Testing & CI

```bash
python manage.py test chat --verbosity=2
```

Every push and pull request against `main` runs the full backend suite against real Postgres and Redis services, checks the health endpoint, and builds the frontend. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Docs

- 📘 [Setup, Deploy & Testing guide](SETUP_DEPLOY_TESTING.md)
- ⚙️ [.env.example](.env.example) — all configuration options, documented inline

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <strong>Upload your data. Ask in plain language. Get answers.</strong>
</p>
