"""
RIFT 2026 — Configuration & Constants
"""
import os
from pathlib import Path
import tempfile

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

# Check if running on Vercel (or other read-only env)
if os.environ.get("VERCEL"):
    # Use /tmp for writable storage in serverless environments
    TEMP_DIR = Path(tempfile.gettempdir())
    CLONE_DIR = TEMP_DIR / "cloned_repos"
    RESULTS_PATH = TEMP_DIR / "results.json"
else:
    # Local development default
    CLONE_DIR = BACKEND_DIR / "cloned_repos"
    RESULTS_PATH = PROJECT_ROOT / "results.json"

# --- Healing Pipeline ---
MAX_ITERATIONS = 5          # default: 5 as per hackathon spec

# --- Scoring ---
BASE_SCORE = 100
TIME_BONUS = 10          # +10 if completed in < 5 minutes
TIME_BONUS_THRESHOLD = 300  # 5 minutes in seconds
COMMIT_PENALTY = 2       # -2 per commit over threshold
COMMIT_THRESHOLD = 20    # penalty kicks in after this many commits

# --- Docker Sandbox ---
SANDBOX_IMAGE = "rift-sandbox:latest"
SANDBOX_TIMEOUT = 120    # seconds per sandbox run

# --- Git Guardrails ---
PROTECTED_BRANCHES = {"main", "master"}
COMMIT_PREFIX = "[AI-AGENT]"

# --- Error Categories ---
ERROR_CATEGORIES = [
    "LINTING",
    "SYNTAX",
    "LOGIC",
    "TYPE_ERROR",
    "IMPORT",
    "INDENTATION",
]

# Ensure clone directory exists
CLONE_DIR.mkdir(parents=True, exist_ok=True)
