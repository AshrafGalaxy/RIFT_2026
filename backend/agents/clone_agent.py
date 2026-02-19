"""
RIFT 2026 — Clone Agent

Clones a GitHub repository to the local workspace.
"""
import logging
import shutil
from pathlib import Path

from config import CLONE_DIR
from services.git_service import git_service

logger = logging.getLogger("rift.clone_agent")


class CloneAgent:
    """Agent responsible for cloning the target repository."""

    def run(self, repo_url: str, team_name: str) -> str:
        """
        Clone the repo into CLONE_DIR/<team_name_sanitized>.

        Args:
            repo_url: GitHub repo URL.
            team_name: Team name (used for folder naming).

        Returns:
            Absolute path to the cloned repo.
        """
        # Sanitize folder name
        folder_name = team_name.strip().replace(" ", "_").upper()
        dest = CLONE_DIR / folder_name

        # Clean up any previous clone
        if dest.exists():
            logger.info(f"Removing previous clone at {dest}")
            shutil.rmtree(dest, ignore_errors=True)

        # Ensure parent directory exists (but NOT dest itself — git clone creates it)
        dest.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning {repo_url} → {dest}")
        git_service.clone_repo(repo_url, str(dest))

        logger.info(f"Clone complete: {dest}")
        return str(dest)


# Singleton
clone_agent = CloneAgent()
