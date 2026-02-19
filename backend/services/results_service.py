"""
RIFT 2026 — Results Service

Reads/writes results.json to the project root.
"""
import json
import logging
from pathlib import Path

from config import RESULTS_PATH
from models import RunResult

logger = logging.getLogger("rift.results_service")


class ResultsService:
    """Persists RunResult as results.json."""

    def save(self, result: RunResult) -> Path:
        """Write RunResult to results.json in project root."""
        data = result.model_dump(mode="json")
        RESULTS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Results saved to {RESULTS_PATH}")
        return RESULTS_PATH

    def load(self) -> dict | None:
        """Load results.json. Returns None if not found."""
        if not RESULTS_PATH.exists():
            return None
        try:
            return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            return None


# Singleton
results_service = ResultsService()
