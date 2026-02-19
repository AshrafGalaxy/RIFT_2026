"""
RIFT 2026 — CrewAI Custom Tools

Wraps our existing agent logic as CrewAI-compatible tools so that
CrewAI agents can invoke them during task execution.
"""
import json
import logging
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger("rift.crewai_tools")


# ===================== CLONE TOOL =====================

class CloneToolInput(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL to clone")
    team_name: str = Field(..., description="Team name for folder naming")


class CloneTool(BaseTool):
    name: str = "clone_repository"
    description: str = (
        "Clones a GitHub repository to a local directory. "
        "Input: repo_url and team_name. Returns the local path."
    )
    args_schema: Type[BaseModel] = CloneToolInput

    def _run(self, repo_url: str, team_name: str) -> str:
        from agents.clone_agent import clone_agent
        try:
            path = clone_agent.run(repo_url, team_name)
            return json.dumps({"status": "success", "repo_path": path})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})


# ===================== DISCOVER TOOL =====================

class DiscoverToolInput(BaseModel):
    repo_path: str = Field(..., description="Local path to the cloned repository")


class DiscoverTool(BaseTool):
    name: str = "discover_and_run_tests"
    description: str = (
        "Scans the repository, detects project type and test framework, "
        "installs dependencies, and runs the test suite inside a sandbox. "
        "Returns stdout, stderr, exit code, and pass/fail counts."
    )
    args_schema: Type[BaseModel] = DiscoverToolInput

    def _run(self, repo_path: str) -> str:
        from agents.discover_agent import discover_agent
        try:
            output = discover_agent.run(repo_path)
            return json.dumps(output.model_dump(), default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})


# ===================== ANALYZE TOOL =====================

class AnalyzeToolInput(BaseModel):
    stdout: str = Field(..., description="Test stdout output")
    stderr: str = Field(..., description="Test stderr output")
    framework: str = Field(..., description="Test framework (pytest, jest, etc.)")
    repo_path: str = Field(..., description="Path to the repository")


class AnalyzeTool(BaseTool):
    name: str = "analyze_errors"
    description: str = (
        "Parses test output (stdout/stderr) and classifies each error "
        "into one of: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION. "
        "Returns a list of classified errors with file, line number, and type."
    )
    args_schema: Type[BaseModel] = AnalyzeToolInput

    def _run(self, stdout: str, stderr: str, framework: str, repo_path: str) -> str:
        from agents.analyze_agent import analyze_agent
        try:
            errors = analyze_agent.run(stdout, stderr, framework, repo_path)
            return json.dumps([e.model_dump() for e in errors], default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})


# ===================== HEAL TOOL =====================

class HealToolInput(BaseModel):
    repo_path: str = Field(..., description="Path to the cloned repository")
    errors_json: str = Field(..., description="JSON string of classified errors")
    team_name: str = Field(..., description="Team name")
    leader_name: str = Field(..., description="Leader name")
    iteration: int = Field(..., description="Current iteration number (1-based)")


class HealTool(BaseTool):
    name: str = "heal_code"
    description: str = (
        "Applies targeted fixes for each classified error. "
        "Creates a fix branch (TEAM_NAME_LEADER_NAME_AI_Fix), "
        "commits each fix with [AI-AGENT] prefix, and pushes to remote. "
        "Returns the list of fixes, branch name, and commit count."
    )
    args_schema: Type[BaseModel] = HealToolInput

    def _run(
        self,
        repo_path: str,
        errors_json: str,
        team_name: str,
        leader_name: str,
        iteration: int,
    ) -> str:
        from agents.heal_agent import heal_agent
        from models import ErrorInfo
        try:
            errors = [ErrorInfo(**e) for e in json.loads(errors_json)]
            fixes, branch_name, commits = heal_agent.run(
                repo_path, errors, team_name, leader_name, iteration
            )
            return json.dumps({
                "fixes": [f.model_dump() for f in fixes],
                "branch_name": branch_name,
                "commit_count": commits,
            }, default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})


# ===================== VERIFY TOOL =====================

class VerifyToolInput(BaseModel):
    repo_path: str = Field(..., description="Path to the cloned repository")


class VerifyTool(BaseTool):
    name: str = "verify_fixes"
    description: str = (
        "Re-runs the full test suite on the fixed branch to check "
        "if all fixes resolved the errors. Returns updated pass/fail counts."
    )
    args_schema: Type[BaseModel] = VerifyToolInput

    def _run(self, repo_path: str) -> str:
        from agents.verify_agent import verify_agent
        try:
            output = verify_agent.run(repo_path)
            return json.dumps(output.model_dump(), default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
