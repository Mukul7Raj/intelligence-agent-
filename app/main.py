import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from app import db, pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

scheduler = BackgroundScheduler()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    interval = int(os.getenv("SCHEDULE_MINUTES", "30"))
    scheduler.add_job(pipeline.run_pipeline, "interval", minutes=interval, id="pipeline_job", replace_existing=True)
    scheduler.start()
    logger.info(f"Background Scheduler started: running pipeline every {interval} minutes")
    yield
    scheduler.shutdown()
    logger.info("Background Scheduler stopped")


app = FastAPI(
    title="LH2 AI LABS — Company Intelligence Agent",
    description="Automated multi-signal intelligence agent pipeline powered by Playwright, Supabase SQL, and Gemini LLM.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
def root_dashboard(request: Request):
    """Serves the interactive glassmorphic visual dashboard."""
    results = db.get_latest_results(limit=100)
    stats = db.get_stats()
    schedule_minutes = os.getenv("SCHEDULE_MINUTES", "30")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "results": results,
            "stats": stats,
            "schedule_minutes": schedule_minutes
        }
    )



@app.post("/run")
def trigger_run(only_unprocessed: bool = Query(default=False, description="If true, only processes rows not yet evaluated")):
    """Manually trigger a pipeline run on demand."""
    run_output = pipeline.run_pipeline(only_unprocessed=only_unprocessed)
    return run_output


@app.get("/results")
def get_results(
    limit: int = Query(default=50, ge=1, le=500),
    fit: bool = Query(default=None, description="Filter by fit (true/false)"),
    search: str = Query(default=None, description="Search by company name, website, or reasoning")
):
    """Query stored database records with optional filtering and search."""
    return db.get_latest_results(limit=limit, fit_filter=fit, search=search)


@app.get("/results/{result_id}")
def get_result_by_id(result_id: int):
    """Retrieve detailed telemetry and LLM reasoning for a specific result."""
    result = db.get_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Company intelligence result not found")
    return result


@app.get("/status")
def status_info():
    """Returns background scheduler status, database metrics, and service state."""
    job = scheduler.get_job("pipeline_job")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "status": "online",
        "service": "company-intelligence-agent",
        "scheduler_running": scheduler.running,
        "schedule_interval_minutes": int(os.getenv("SCHEDULE_MINUTES", "30")),
        "next_scheduled_run": next_run,
        "stats": db.get_stats()
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

