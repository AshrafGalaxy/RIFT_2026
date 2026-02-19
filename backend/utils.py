"""
RIFT 2026 — Utility Helpers
"""
import re
from datetime import datetime

from config import (
    BASE_SCORE,
    COMMIT_PENALTY,
    COMMIT_THRESHOLD,
    TIME_BONUS,
    TIME_BONUS_THRESHOLD,
)


def format_branch_name(team_name: str, leader_name: str) -> str:
    """
    Format branch name per hackathon rules:
    - All UPPERCASE
    - Spaces → underscores
    - Remove brackets and special chars
    - Append _AI_Fix
    Example: "Code Warriors", "John Doe" → CODE_WARRIORS_JOHN_DOE_AI_Fix
    """
    raw = f"{team_name}_{leader_name}"
    # Remove brackets, parentheses, and other special chars
    cleaned = re.sub(r"[\[\]\(\)\{\}<>\"'`~!@#$%^&*+=|\\/:;,?.]", "", raw)
    # Replace spaces and multiple underscores with single underscore
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    # Strip leading/trailing underscores
    cleaned = cleaned.strip("_")
    # Uppercase
    branch = f"{cleaned}_AI_Fix".upper()
    # Fix the suffix — must be exactly _AI_Fix (mixed case as per spec)
    branch = branch[: -len("_AI_FIX")] + "_AI_Fix"
    return branch


def compute_score(
    total_commits: int,
    elapsed_seconds: float,
    all_passed: bool,
) -> int:
    """
    Score = BASE_SCORE
         + TIME_BONUS if < 5 minutes
         - COMMIT_PENALTY * max(0, total_commits - COMMIT_THRESHOLD)
    Clamped to [0, 120].
    """
    if not all_passed:
        return 0

    score = BASE_SCORE

    # Time bonus
    if elapsed_seconds < TIME_BONUS_THRESHOLD:
        score += TIME_BONUS

    # Commit penalty
    excess_commits = max(0, total_commits - COMMIT_THRESHOLD)
    score -= COMMIT_PENALTY * excess_commits

    return max(0, min(score, 120))


def now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.utcnow().isoformat()


def format_commit_message(bug_type: str, file: str, line: int) -> str:
    """Generate a commit message with the required [AI-AGENT] prefix."""
    return f"[AI-AGENT] Fix {bug_type} in {file}:{line}"
