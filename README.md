<p align="center">
  <!-- TODO: add logo -->
  <!--
  <picture>
    <source srcset="frontend/public/logo-dark.svg" media="(prefers-color-scheme: dark)">
    <source srcset="frontend/public/logo-light.svg" media="(prefers-color-scheme: light)">
    <img src="frontend/public/logo-light.svg" alt="Nura Intelligence" width="400" />
  </picture>
  -->
</p>

<p align="center">
  <strong>conversational business intelligence for e-commerce data. <br>upload a dataset, ask questions in plain language, get answers, charts and reports.</strong>
</p>

<p align="center">
  <a href="#quickstart">Start</a> ·
  <a href="#architecture">Backend</a> ·
  <a href="#api-reference">API</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/backend-django-success?style=flat-square" alt="backend" />
  <img src="https://img.shields.io/badge/frontend-react-success?style=flat-square" alt="frontend" />
  <img src="https://img.shields.io/badge/license-apache-lightgrey?style=flat-square" alt="license" />
</p>

---

<p align="justify">
NURA INTELLIGENCE is a conversational Business Intelligence platform. You upload a dataset (CSV, XLSX or JSON), the platform cleans it, profiles it and hands it to an AI engine that can be asked questions in natural language — and it also looks for things in the data on its own, without being asked.
</p>

<p align="justify">
It ships with a working example built around three e-commerce marketplaces — Temu, Shein and AliExpress — but the data engine, chat and analytics layers are domain-agnostic: any tabular dataset works.
</p>

<!--<img src="https://via.placeholder.com/1400x820?text=Chat+%2B+Dashboard+screenshot" alt="Nura Intelligence product screenshot" width="100%" />
-->

| | |
|---|---|
| **Conversational analytics** | Chat with your dataset — ask for trends, comparisons, breakdowns — with full context of the active dataset and conversation history. |
| **Automatic data engine** | Format detection, null handling, type inference, deduplication. Raw files become clean, versioned internal datasets. |
| **Proactive insights** | Correlations, distributions, anomaly detection (Isolation Forest) and auto-computed KPIs — surfaced without being asked. |
| **Visualizations & dashboards** | Bar, line, pie, heatmap and scatter charts, exportable to PNG/SVG/PDF. Build dashboards manually or let the AI generate them. |
| **Automated reports** | Executive, technical and financial reports, exportable to PDF/DOCX/PPTX. |
| **Automation & triggers** | New file, detected anomaly or scheduled date — automatically analyze, notify or generate a report. |
| **Collaboration** | Organizations, roles, sharing and comments on top of a multiuser workspace model. |
| **Enterprise AI** | Specialized agents per business area (finance, sales, marketing, operations), "what-if" simulations and proactive recommendations. |

---

## Use Nura Intelligence

<table>
<tr>
<td width="50%" valign="top">

<h3>I want to analyze my data</h3>

<p align="justify">Upload a CSV/XLSX/JSON file, let the data engine clean and profile it, then just ask questions in natural language.</p>

**[→ Jump to Quickstart](#quickstart)**

</td>
<td width="50%" valign="top">

<h3>I'm extending the platform</h3>

<p align="justify">Each module is an independent Django app/service under <code>services/</code>, with its own models, tests and, where it applies, Celery tasks.</p>

**[→ Jump to Architecture](#architecture)**

</td>
</tr>
<tr>
<td colspan="2" valign="top">

<h3>I want to deploy it</h3>

<p align="justify">Docker Compose setup with Postgres, Redis, a Celery worker and an Nginx-served frontend. See the Quickstart section below for the commands, and Architecture for how the pieces fit together.</p>

**[→ Jump to Quickstart](#quickstart)**

</td>
</tr>
</table>

---

## Quickstart

### 1. Backend (Django)

```bash
cp .env.example .env
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser                    # optional, for /admin/
python manage.py runserver
```

<p align="justify">If <code>DATABASE_URL</code> is not set in <code>.env</code>, the project falls back to SQLite automatically — no local Postgres required to try it out.</p>

### 2. Frontend (React + Vite), in another terminal

```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

### 3. Open the app

<p align="justify"><strong>http://localhost:5173</strong> is the user interface.</p>

<p align="justify"><code>http://localhost:8000</code> is only the backend API (you will see a status page, not the app).</p>

### AI chat

<p align="justify">The conversational engine needs at least one LLM provider key in <code>.env</code> (<code>GROQ_API_KEY</code>, <code>CEREBRAS_API_KEY</code> or <code>OPENROUTER_API_KEY</code>). Without one, the rest of the platform (auth, dataset upload, etc.) still works, but the chat will return an error.</p>

### Try it with sample data

```bash
python scripts/generar_dataset_ejemplo.py
```

<p align="justify">Generates a realistic 200-row e-commerce dataset (Temu/Shein/AliExpress orders), deliberately imperfect — nulls, a couple of price outliers and a duplicate row — so there is something real for the analytics engine to detect end to end.</p>

### Run with Docker

```bash
cd docker
docker compose up --build
```

<p align="justify">This spins up Postgres, Redis, the Django service, a Celery worker, an Nginx gateway and the frontend dev server, each with health checks.</p>

---

## Modules

<!--<img src="https://via.placeholder.com/1000x500?text=Module+diagram" alt="Module diagram" width="80%" />
-->

| # | Module | What it does |
|---|--------|---------------|
| 1 | **Accounts & Workspace** | Full auth (register, login, password recovery, profile), an auto-provisioned workspace per user, and file upload/management (CSV, XLSX, JSON) with validation and metadata. |
| 2 | **Data Engine** | Automatic reading and cleaning (format detection, nulls, types, duplicates), file-to-internal-dataset conversion, and dataset CRUD: versioning, merging, exploration, basic statistics. |
| 3 | **Conversational AI + Analytics** | Chat with context of the active dataset and conversation history; analytical engine for correlations, distributions, anomalies and automatic KPIs. The AI also surfaces findings proactively. |
| 4 | **Visualization & Reports** | Charts (bar, line, pie, heatmap, scatter) exportable to PNG/SVG/PDF; buildable dashboards (manual or AI-generated); automated executive/technical/financial reports exportable to PDF/DOCX/PPTX. |
| 5 | **Automation & Collaboration** | Triggers (new file, anomaly, date) that fire actions (analyze, notify, generate report); multiuser model with organizations, roles, sharing and comments; external data-source integration via read-only queries against external databases. |
| 6 | **Enterprise AI** | Specialized agents per business area (finance, sales, marketing, operations), "what-if" simulations, proactive recommendations, two-factor authentication (TOTP), and a documented public REST API. |

---

## Architecture

```
nura/
├── docker/          # docker-compose, Nginx config, Dockerfiles
├── frontend/        # React + Vite + TypeScript + Tailwind SPA
├── nura/            # Django project config (settings, urls, celery app)
├── services/
│   ├── chat/        # Modules 1, 3 (chat), 4, 5, 6 — Django app: models, views, tasks
│   ├── ai/          # LLM integration, agents, prompts
│   └── analytics/   # Module 2, 3 (analytics) — cleaning, anomalies, trends, scoring
└── scripts/         # utility & sample-data scripts
```

<p align="justify">
<strong>Infrastructure:</strong> Docker, Docker Compose, environment variables, GitHub Actions CI/CD, structured logging, optional Sentry monitoring, Django/pytest test suite.
</p>

<p align="justify">
<strong>Backend:</strong> Django 6, Django REST Framework, JWT authentication (SimpleJWT, dj-rest-auth, allauth), Celery, Redis, PostgreSQL with a SQLite fallback for local development, pandas and scikit-learn for the analytics engine, drf-spectacular for the public API schema.
</p>

<p align="justify">
<strong>Frontend:</strong> React 19, Vite, Tailwind CSS, Chart.js.
</p>

<!--<img src="https://via.placeholder.com/900x160?text=Tech+stack+logos" alt="Tech stack" width="70%" />
-->

---

## API reference

<p align="justify">With the backend running, interactive API documentation is available at:</p>

- `http://localhost:8000/api/docs/` — Swagger UI
- `http://localhost:8000/api/redoc/` — Redoc
- `http://localhost:8000/healthz/` — health check (database + cache)

<!--<img src="https://via.placeholder.com/1200x700?text=Swagger+UI+screenshot" alt="API docs screenshot" width="100%" />
-->

---

## Testing & CI

```bash
python manage.py test chat --verbosity=2
```

<p align="justify">
Every push and pull request against <code>main</code> runs the full backend suite against real Postgres and Redis services, checks the health endpoint, and builds the frontend. See <a href=".github/workflows/ci.yml"><code>.github/workflows/ci.yml</code></a>.
</p>

---

## Author

**Emily Monterrosa Castro - Full Stack Developer** <br>
[GitHub](https://github.com/emilymontec) · [LinkedIn](https://www.linkedin.com/in/emilymontec/) · [Portfolio](https://emilymontec.github.io/portfolio/)

---

## License

Apache License 2.0

See the [LICENSE](LICENSE) file for additional information.

<!--
## Appendices
See the [UserGuide](docs/MANUAL%20USUARIO%20KEISY%20MEDICAL.pdf) to learn more.

If you want to know more about the system, please check the [Documentation](docs/DOCUMENTACION%20TECNICA%20KEISY%20MEDICAL.pdf).
-->

---

<p align="center">
  <strong>upload your data.<br>ask in plain language.<br>get answers.</strong>
</p>