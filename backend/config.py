"""
RIFT 2026 — Configuration & Constants
"""
import os
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
CLONE_DIR = BACKEND_DIR / "cloned_repos"
RESULTS_PATH = PROJECT_ROOT / "results.json"

# --- Healing Pipeline ---
MAX_ITERATIONS = 5

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
