<<<<<<< HEAD
# LH2 AI LABS — Company Intelligence Agent

An automated, end-to-end company intelligence pipeline: target companies enter via a Google Sheet, the system enriches each company with multi-source signals (including headless browser automation with Playwright), persists structured evidence to a SQL database, evaluates fit using a Gemini LLM, writes verdicts back to Google Sheets, and runs continuously on a schedule — fully containerized, deployed, and wired to GitHub Actions.

![Dashboard Preview](docs/dashboard.png)

---

## 🏛️ Architecture

```
                    +-----------------------------+
                    |  Google Sheet (Source)      |
                    +--------------+--------------+
                                   |
                            read_companies()
                                   |
                                   v
                        +----------+----------+
                        |  Enrichment Engine  |
                        +----+-----------+----+
                             |           |
                HTTP Signal  |           | Playwright Browser
               (Status/Meta) |           | (Title/H1/Snippet)
                             v           v
                        +----+-----------+----+
                        |  Gemini LLM Judge   |
                        | (Reasoning Verdict) |
                        +----------+----------+
                                   |
                                   v
                +------------------+------------------+
                |                                     |
                v                                     v
    +-----------+-----------+             +-----------+-----------+
    | Postgres / SQLite DB  |             | Google Sheet (Sync Back)  |
    |  (Persisted Evidence) |             |  (Fit/Confidence/Q's)     |
    +-----------+-----------+             +---------------------------+
                ^
                |
    +-----------+-------------------------------------+
    | FastAPI Web App & Visual Dashboard               |
    |  - GET /            -> Glassmorphic Dashboard UI|
    |  - POST /run        -> On-demand Execution      |
    |  - GET /results     -> Query Database Verdicts  |
    |  - GET /status      -> Pipeline & Schedule Info |
    +-------------------------------------------------+
```

---

## 💡 Why These Tech Stack Choices?

- **Playwright (Chromium)** for browser automation: Catches client-side JavaScript-rendered content, SPA titles, meta descriptions, and visible text snippets that plain HTTP GET calls miss entirely.
- **Supabase (PostgreSQL) / SQLite**: Production runs use standard PostgreSQL via Supabase/Neon. Local runs fall back seamlessly to SQLite (`company_intelligence.db`) without requiring database setup.
- **Google Gemini API**: Free-tier LLM generating structured JSON outputs (`fit`, `confidence`, `follow_up_question`, `reasoning`) with evidence-based reasoning over raw text summaries.
- **FastAPI + APScheduler**: Single lightweight Python process serving the visual web dashboard, REST API endpoints, and executing background intervals (`SCHEDULE_MINUTES`).
- **GitHub Actions**:
  - `ci.yml`: Runs automated syntax compilation and `pytest` suite on every push.
  - `trigger-pipeline.yml`: Scheduled GitHub Actions workflow calling the live deployed `/run` endpoint automatically on a cron schedule with zero human intervention.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GOOGLE_SHEET_ID` | Spreadsheet ID from Google Sheets URL | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account file path OR raw JSON string | `./service_account.json` or `{"type": "service_account"...}` |
| `DATABASE_URL` | PostgreSQL or SQLite connection string | `postgresql://user:pass@host:5432/postgres` (defaults to SQLite if omitted) |
| `GEMINI_API_KEY` | Free Gemini API key from Google AI Studio | `AIzaSy...` |
| `SCHEDULE_MINUTES` | Pipeline background execution interval | `30` |

---

## 🚀 Quickstart (Run Locally)

### 1. Install Dependencies & Playwright Browser

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Launch FastAPI Server

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser to view the **Glassmorphic Interactive Dashboard**.

---

## 🧪 Running Automated Tests

Run the complete test suite:

```bash
pytest -v
```

---

## 🐳 Docker Deployment

Build and run the containerized application locally:

```bash
docker build -t company-intelligence-agent .
docker run -p 8000:8000 --env-file .env company-intelligence-agent
```

---

## 🌐 Production Deployment Guide

Deploy to Render, Railway, Fly.io, or Koyeb:

1. **Create Web Service**: Connect your GitHub repository.
2. **Environment Variables**: Add `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DATABASE_URL`, and `GEMINI_API_KEY`.
3. **Build & Start Command**: Uses `Dockerfile` automatically or command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Set repo secret `PIPELINE_URL` in GitHub (`Settings -> Secrets and variables -> Actions`) pointing to your live app URL (e.g., `https://company-intelligence-agent.onrender.com`).

---

## 🤖 GitHub Actions Integration

- **`ci.yml`**: Validates syntax, imports, and executes pytest on every push to `main`/`master`.
- **`trigger-pipeline.yml`**: Sends a POST request to `${{ secrets.PIPELINE_URL }}/run` on a hourly cron schedule.

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /` | `GET` | Glassmorphic visual web dashboard |
| `POST /run` | `POST` | Trigger pipeline on demand (`?only_unprocessed=true` supported) |
| `GET /results` | `GET` | Query stored verdicts (`?limit=50&fit=true&search=Acme`) |
| `GET /results/{id}` | `GET` | Detailed telemetry & LLM evidence for a single result |
| `GET /status` | `GET` | Scheduler status, next run time, and DB statistics |
| `GET /health` | `GET` | Health check endpoint |

---

## 🎥 3-5 Minute Demo Video Presentation Guide

For your application video submission, structure your 3-5 minute presentation as follows:

1. **Introduction (30s)**: Introduce yourself, mention your interest in the Founder's Office - Automation Intern role at LH2 AI Labs.
2. **Architecture Walkthrough (1m)**: Highlight the 5-stage pipeline (Source -> Enrich -> Persist -> Judge -> Sync Back) and explain why Playwright was chosen over plain HTTP calls to capture rendered SPAs.
3. **Live Demonstration (2m)**:
   - Show the Google Sheet with initial company rows.
   - Open the live URL (`GET /`) showing the glassmorphic dashboard.
   - Click "Run Pipeline On-Demand" live and show real-time processing.
   - Inspect the "Signals & Reasoning" modal displaying Playwright browser text vs HTTP telemetry.
   - Show the Google Sheet auto-updating with `Fit`, `Confidence`, `Follow-Up Question`, and `Reasoning`.
4. **Automation & GitHub Integration (30s)**: Show `ci.yml` and `trigger-pipeline.yml` keeping the pipeline running autonomously.
