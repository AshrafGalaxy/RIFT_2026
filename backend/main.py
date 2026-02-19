"""
RIFT 2026 — FastAPI Application

Endpoints:
  POST /api/run      — Start the self-healing pipeline
  GET  /api/results   — Get the latest results.json
  GET  /api/health    — Health check
"""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import RunRequest, RunResult
from crew_orchestrator import run_pipeline
from services.results_service import results_service

# ---------- Logging ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rift")

# ---------- FastAPI App ----------

app = FastAPI(
    title="RIFT 2026 — Self-Healing CI/CD",
    description="Autonomous self-healing CI/CD agent backend",
    version="1.0.0",
)

# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",  # Allow all for hackathon demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Routes ----------

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "RIFT Self-Healing CI/CD",
        "version": "1.0.0",
    }


@app.post("/api/run", response_model=RunResult)
async def start_run(request: RunRequest):
    """
    Start the self-healing pipeline.

    Accepts:
        - repo_url: GitHub repository URL
        - team_name: Hackathon team name
        - leader_name: Team leader name

    Returns:
        RunResult with all fixes, iterations, score, and status.
    """
    logger.info("=" * 70)
    logger.info("NEW RUN REQUEST")
    logger.info(f"  Repo:   {request.repo_url}")
    logger.info(f"  Team:   {request.team_name}")
    logger.info(f"  Leader: {request.leader_name}")
    logger.info("=" * 70)

    try:
        result = await run_pipeline(request)
        return result
    except Exception as e:
        logger.error(f"Run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def get_results():
    """Return the latest results.json."""
    data = results_service.load()
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="No results found. Run the pipeline first.",
        )
    return data


# ---------- Startup Event ----------

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 RIFT Self-Healing CI/CD backend started")
    logger.info(f"   Docs: http://localhost:8000/docs")


# ---------- Run ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000,
        reload=True,
        reload_excludes=["cloned_repos/*", "cloned_repos/**"],
    )
