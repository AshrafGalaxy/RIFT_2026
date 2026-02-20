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

        # Clean up any previous clone — robust for Windows file locks
        if dest.exists():
            logger.info(f"Removing previous clone at {dest}")
            self._force_remove(dest)

        # Ensure parent directory exists (but NOT dest itself — git clone creates it)
        dest.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning {repo_url} → {dest}")
        git_service.clone_repo(repo_url, str(dest))

        logger.info(f"Clone complete: {dest}")
        return str(dest)

    @staticmethod
    def _force_remove(path: Path) -> None:
        """Remove a directory tree, handling Windows file locks."""
        import time
        import os
        import stat

        def _on_rm_error(func, fpath, exc_info):
            """Handle permission errors on Windows by forcing writable."""
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)

        # Attempt 1: standard rmtree with permission fix
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            return
        except Exception as e:
            logger.warning(f"rmtree attempt 1 failed: {e}")

        # Attempt 2: retry immediately\n
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            return
        except Exception as e:
            logger.warning(f"rmtree attempt 2 failed: {e}")

        # Attempt 3: fallback to OS-level force delete (Windows)
        if os.name == 'nt':
            os.system(f'rmdir /s /q "{path}"')
        else:
            os.system(f'rm -rf "{path}"')

        if path.exists():
            raise RuntimeError(
                f"Cannot remove previous clone at '{path}'. "
                f"Close any editors/terminals using this directory, then retry."
            )


# Singleton
clone_agent = CloneAgent()
