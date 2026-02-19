"""
RIFT 2026 — Discover Agent

Scans the cloned repo to detect project type, test framework,
installs dependencies, and runs the test suite inside a Docker sandbox.
"""
import logging
import os
from pathlib import Path

from models import TestOutput
from services.docker_service import docker_service

logger = logging.getLogger("rift.discover_agent")


# --- Framework detection patterns ---

PYTHON_TEST_PATTERNS = [
    "test_*.py",
    "*_test.py",
    "tests/*.py",
    "tests/**/*.py",
]

NODE_TEST_PATTERNS = [
    "*.test.js",
    "*.test.ts",
    "*.spec.js",
    "*.spec.ts",
    "__tests__/**",
]


class DiscoverAgent:
    """Agent that discovers project type, installs deps, and runs tests."""

    def run(self, repo_path: str) -> TestOutput:
        """
        Discover and execute the test suite.

        Returns:
            TestOutput with stdout, stderr, exit_code, and parsed pass/fail counts.
        """
        logger.info(f"Discovering project at {repo_path}")

        project_type = self._detect_project_type(repo_path)
        framework = self._detect_test_framework(repo_path, project_type)
        commands = self._build_commands(repo_path, project_type, framework)

        logger.info(f"Project: {project_type}, Framework: {framework}")
        logger.info(f"Commands: {commands}")

        # Run in sandbox
        result = docker_service.run_sandbox(repo_path, commands)

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", -1)

        # Parse test counts from output
        passed, failed, total = self._parse_test_counts(
            stdout, stderr, framework
        )

        output = TestOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            passed=passed,
            failed=failed,
            total=total,
            framework=framework,
        )

        logger.info(
            f"Test results: {passed} passed, {failed} failed, {total} total"
        )
        return output

    # ---- Internal helpers ----

    def _detect_project_type(self, repo_path: str) -> str:
        """Detect if Python or Node project."""
        p = Path(repo_path)

        if (p / "requirements.txt").exists():
            return "python"
        if (p / "Pipfile").exists():
            return "python"
        if (p / "pyproject.toml").exists():
            return "python"
        if (p / "setup.py").exists():
            return "python"
        if (p / "package.json").exists():
            return "node"

        # Fallback: check for .py or .js files
        py_files = list(p.rglob("*.py"))
        js_files = list(p.rglob("*.js")) + list(p.rglob("*.ts"))

        if len(py_files) >= len(js_files):
            return "python"
        return "node"

    def _detect_test_framework(self, repo_path: str, project_type: str) -> str:
        """Detect which test framework is being used."""
        p = Path(repo_path)

        if project_type == "python":
            # Check for pytest in requirements
            for req_file in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
                req_path = p / req_file
                if req_path.exists():
                    content = req_path.read_text(encoding="utf-8", errors="replace")
                    if "pytest" in content.lower():
                        return "pytest"

            # Check pyproject.toml
            pyproject = p / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text(encoding="utf-8", errors="replace")
                if "pytest" in content.lower():
                    return "pytest"

            # Check for conftest.py (pytest marker)
            if list(p.rglob("conftest.py")):
                return "pytest"

            # Check for unittest-style test files
            for test_file in p.rglob("test_*.py"):
                content = test_file.read_text(encoding="utf-8", errors="replace")
                if "unittest" in content:
                    return "unittest"

            return "pytest"  # default for Python

        elif project_type == "node":
            pkg_json = p / "package.json"
            if pkg_json.exists():
                import json
                try:
                    pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                    dev_deps = pkg.get("devDependencies", {})
                    deps = pkg.get("dependencies", {})
                    all_deps = {**deps, **dev_deps}

                    if "jest" in all_deps:
                        return "jest"
                    if "mocha" in all_deps:
                        return "mocha"
                    if "vitest" in all_deps:
                        return "vitest"

                    # Check scripts for test runner hints
                    scripts = pkg.get("scripts", {})
                    test_script = scripts.get("test", "")
                    if "jest" in test_script:
                        return "jest"
                    if "mocha" in test_script:
                        return "mocha"
                    if "vitest" in test_script:
                        return "vitest"
                except json.JSONDecodeError:
                    pass

            return "jest"  # default for Node

        return "unknown"

    def _build_commands(
        self, repo_path: str, project_type: str, framework: str
    ) -> list[str]:
        """Build install + test commands."""
        commands = []

        if project_type == "python":
            # Install deps
            p = Path(repo_path)
            if (p / "requirements.txt").exists():
                commands.append("pip install -r requirements.txt")
            elif (p / "Pipfile").exists():
                commands.append("pip install pipenv && pipenv install --dev")
            elif (p / "pyproject.toml").exists():
                commands.append("pip install -e '.[dev,test]' 2>/dev/null || pip install -e .")
            elif (p / "setup.py").exists():
                commands.append("pip install -e .")

            # Run tests
            if framework == "pytest":
                commands.append("python -m pytest -v --tb=short 2>&1")
            elif framework == "unittest":
                commands.append("python -m unittest discover -v 2>&1")
            else:
                commands.append("python -m pytest -v --tb=short 2>&1")

        elif project_type == "node":
            commands.append("npm install")
            commands.append("npm test 2>&1")

        return commands

    def _parse_test_counts(
        self, stdout: str, stderr: str, framework: str
    ) -> tuple[int, int, int]:
        """Parse pass/fail/total counts from test output."""
        import re

        combined = stdout + "\n" + stderr
        passed = 0
        failed = 0
        total = 0

        if framework == "pytest":
            # Pytest summary line: "X passed, Y failed"
            match = re.search(
                r"(\d+)\s+passed", combined
            )
            if match:
                passed = int(match.group(1))

            match = re.search(
                r"(\d+)\s+failed", combined
            )
            if match:
                failed = int(match.group(1))

            match = re.search(
                r"(\d+)\s+error", combined
            )
            if match:
                failed += int(match.group(1))

            total = passed + failed

        elif framework == "unittest":
            # "Ran X tests"
            match = re.search(r"Ran\s+(\d+)\s+test", combined)
            if match:
                total = int(match.group(1))

            # "FAILED (failures=X, errors=Y)"
            fail_match = re.search(r"failures=(\d+)", combined)
            err_match = re.search(r"errors=(\d+)", combined)
            if fail_match:
                failed += int(fail_match.group(1))
            if err_match:
                failed += int(err_match.group(1))

            passed = max(0, total - failed)

        elif framework in ("jest", "vitest"):
            # "Tests: X failed, Y passed, Z total"
            match = re.search(
                r"Tests:\s+(\d+)\s+failed,\s+(\d+)\s+passed,\s+(\d+)\s+total",
                combined,
            )
            if match:
                failed = int(match.group(1))
                passed = int(match.group(2))
                total = int(match.group(3))
            else:
                # "Tests: Y passed, Z total"
                match = re.search(
                    r"Tests:\s+(\d+)\s+passed,\s+(\d+)\s+total", combined
                )
                if match:
                    passed = int(match.group(1))
                    total = int(match.group(2))
                    failed = total - passed

        elif framework == "mocha":
            # "X passing" / "Y failing"
            match = re.search(r"(\d+)\s+passing", combined)
            if match:
                passed = int(match.group(1))
            match = re.search(r"(\d+)\s+failing", combined)
            if match:
                failed = int(match.group(1))
            total = passed + failed

        # Fallback: try generic patterns
        if total == 0:
            # Count "PASSED" / "FAILED" / "OK" occurrences
            passed = len(re.findall(r"\bPASS(?:ED)?\b", combined, re.IGNORECASE))
            failed = len(re.findall(r"\bFAIL(?:ED)?\b", combined, re.IGNORECASE))
            total = passed + failed

        return passed, failed, total


# Singleton
discover_agent = DiscoverAgent()
