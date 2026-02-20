"""
RIFT 2026 — Git Service

Handles branch creation, committing with [AI-AGENT] prefix, and pushing.
Enforces guardrails: no push to main/master.
"""
import logging
from pathlib import Path

from git import Repo, GitCommandError

from config import COMMIT_PREFIX, PROTECTED_BRANCHES
from utils import format_branch_name

logger = logging.getLogger("rift.git_service")


class GitService:
    """Git operations with hackathon guardrails enforced."""

    def clone_repo(self, repo_url: str, dest_path: str) -> Repo:
        """Clone a repository to dest_path (shallow, single-branch for speed)."""
        logger.info(f"Cloning {repo_url} → {dest_path} (shallow)")
        repo = Repo.clone_from(
            repo_url, dest_path,
            depth=1,
            single_branch=True,
        )
        # Unshallow so we can create branches and push
        try:
            repo.git.fetch('--unshallow')
        except GitCommandError:
            pass  # Already unshallowed or not needed
        return repo

    def create_branch(
        self, repo: Repo, team_name: str, leader_name: str
    ) -> str:
        """
        Create and checkout the fix branch.
        Branch name: TEAM_NAME_LEADER_NAME_AI_Fix
        """
        branch_name = format_branch_name(team_name, leader_name)
        logger.info(f"Creating branch: {branch_name}")

        # Create branch from current HEAD
        if branch_name in [b.name for b in repo.branches]:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout("-b", branch_name)

        return branch_name

    def commit_fix(
        self,
        repo: Repo,
        file_path: str,
        commit_message: str,
    ) -> str:
        """
        Stage a file and commit with [AI-AGENT] prefix.

        Returns:
            The commit SHA.
        """
        # Enforce commit prefix
        if not commit_message.startswith(COMMIT_PREFIX):
            commit_message = f"{COMMIT_PREFIX} {commit_message}"

        # Stage
        repo.index.add([file_path])
        # Commit
        commit = repo.index.commit(commit_message)
        logger.info(f"Committed: {commit_message} ({commit.hexsha[:8]})")
        return commit.hexsha

    def push(self, repo: Repo, branch_name: str) -> bool:
        """
        Push branch to origin. Blocks push to protected branches.

        Returns:
            True if push succeeded.
        """
        # GUARDRAIL: never push to main/master
        if branch_name.lower() in {b.lower() for b in PROTECTED_BRANCHES}:
            logger.error(
                f"BLOCKED: Cannot push to protected branch '{branch_name}'"
            )
            raise ValueError(
                f"Push to protected branch '{branch_name}' is forbidden."
            )

        try:
            origin = repo.remote("origin")
            origin.push(branch_name)
            logger.info(f"Pushed branch '{branch_name}' to origin.")
            return True
        except GitCommandError as e:
            logger.error(f"Push failed: {e}")
            return False

    def get_repo(self, repo_path: str) -> Repo:
        """Open an existing repo."""
        return Repo(repo_path)

    def get_current_branch(self, repo: Repo) -> str:
        """Return the active branch name."""
        return repo.active_branch.name


# Singleton
git_service = GitService()
