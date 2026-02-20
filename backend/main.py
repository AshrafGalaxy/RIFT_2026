"""
RIFT 2026 — FastAPI Application

Endpoints:
  POST /api/run         — Start the self-healing pipeline (blocking, returns JSON)
  POST /api/run-stream  — Start with SSE streaming for real-time progress
  GET  /api/results     — Get the latest results.json
  GET  /api/health      — Health check
"""
import asyncio
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import RunRequest, RunResult
from crew_orchestrator import run_pipeline
from services.results_service import results_service
from sse_manager import SSEManager

# ---------- Logging ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rift")

# Thread pool for running sync pipeline code without blocking the event loop
_executor = ThreadPoolExecutor(max_workers=2)

# ---------- FastAPI App ----------

app = FastAPI(
    title="RIFT 2026 — Self-Healing CI/CD",
    description="Autonomous self-healing CI/CD agent backend",
    version="1.0.0",
)

# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Routes ----------

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RIFT Self-Healing CI/CD",
        "version": "1.0.0",
    }


@app.post("/api/run", response_model=RunResult)
async def start_run(request: RunRequest):
    """Start the pipeline (blocking — no streaming)."""
    logger.info(f"NEW RUN (blocking): {request.repo_url}")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: asyncio.run(run_pipeline(request))
        )
        return result
    except Exception as e:
        logger.error(f"Run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-stream")
async def start_run_stream(request: RunRequest):
    """
    Start pipeline with SSE streaming.
    Pipeline runs in a THREAD so the event loop stays free to yield events.
    """
    logger.info(f"NEW RUN (SSE): {request.repo_url}")

    loop = asyncio.get_event_loop()
    sse = SSEManager()
    queue = sse.create_queue(loop)

    def run_sync():
        """Run the async pipeline from within a thread."""
        try:
            asyncio.run(run_pipeline(request, sse=sse))
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            sse.error(str(e))
            sse.done()

    # Run pipeline in thread executor → event loop stays free to yield SSE
    loop.run_in_executor(_executor, run_sync)

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                event_type = event.get("event", "log")
                data = event.get("data", "")
                yield f"event: {event_type}\ndata: {data}\n\n"
                if event_type == "done":
                    break
            except asyncio.TimeoutError:
                yield f": keepalive\n\n"
            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/results")
async def get_results():
    data = results_service.load()
    if data is None:
        raise HTTPException(status_code=404, detail="No results found.")
    return data


@app.on_event("startup")
async def on_startup():
    logger.info("RIFT Self-Healing CI/CD backend started")
    logger.info("   Docs: http://localhost:8000/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000,
        reload=True,
        reload_excludes=["cloned_repos/*", "cloned_repos/**"],
    )
