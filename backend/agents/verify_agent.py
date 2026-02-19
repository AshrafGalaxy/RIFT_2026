"""
RIFT 2026 — Verify Agent

Re-runs the test suite on the fixed branch to check if fixes resolved the errors.
"""
import logging

from models import TestOutput
from services.docker_service import docker_service
from agents.discover_agent import DiscoverAgent

logger = logging.getLogger("rift.verify_agent")


class VerifyAgent:
    """Agent that re-runs tests after fixes are applied."""

    def __init__(self):
        self._discover = DiscoverAgent()

    def run(self, repo_path: str) -> TestOutput:
        """
        Re-run the full test suite on the fixed branch.

        Returns:
            TestOutput with updated pass/fail counts.
        """
        logger.info(f"Verifying fixes in {repo_path}")

        # Re-use discover agent's detection and execution logic
        output = self._discover.run(repo_path)

        if output.exit_code == 0 and output.failed == 0:
            logger.info("✅ All tests PASSED!")
        else:
            logger.info(
                f"❌ Tests still failing: {output.failed} failed, "
                f"{output.passed} passed"
            )

        return output


# Singleton
verify_agent = VerifyAgent()
