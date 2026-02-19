"""
RIFT 2026 — Pydantic Models
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Enums ----------

class BugType(str, Enum):
    LINTING = "LINTING"
    SYNTAX = "SYNTAX"
    LOGIC = "LOGIC"
    TYPE_ERROR = "TYPE_ERROR"
    IMPORT = "IMPORT"
    INDENTATION = "INDENTATION"


class RunStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class FixStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


# ---------- Request ----------

class RunRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL to clone")
    team_name: str = Field(..., description="Hackathon team name")
    leader_name: str = Field(..., description="Team leader's name")


# ---------- Fix ----------

class Fix(BaseModel):
    file: str = Field(..., description="Relative path of the file")
    bug_type: BugType = Field(..., description="Classified error category")
    line_number: int = Field(..., description="Line number of the error")
    original_code: str = Field(default="", description="Original problematic code")
    fixed_code: str = Field(default="", description="Applied fix")
    commit_message: str = Field(default="", description="Git commit message")
    status: FixStatus = Field(default=FixStatus.PENDING)


# ---------- Iteration ----------

class Iteration(BaseModel):
    number: int = Field(..., description="Iteration index (1-based)")
    passed: int = Field(default=0, description="Number of tests passed")
    failed: int = Field(default=0, description="Number of tests failed")
    total: int = Field(default=0, description="Total tests discovered")
    errors_found: int = Field(default=0, description="Errors detected by analyzer")
    fixes_applied: int = Field(default=0, description="Fixes applied by healer")
    status: RunStatus = Field(default=RunStatus.RUNNING)
    stdout: str = Field(default="", description="Test stdout")
    stderr: str = Field(default="", description="Test stderr")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------- Run Result ----------

class RunResult(BaseModel):
    repo_url: str
    branch_name: str
    team_name: str
    leader_name: str
    fixes: List[Fix] = Field(default_factory=list)
    iterations: List[Iteration] = Field(default_factory=list)
    total_commits: int = Field(default=0)
    score: int = Field(default=100)
    status: RunStatus = Field(default=RunStatus.RUNNING)
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None
    error_message: Optional[str] = None


# ---------- Test Output ----------

class TestOutput(BaseModel):
    """Raw output from a test run inside the sandbox."""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    passed: int = 0
    failed: int = 0
    total: int = 0
    framework: str = "unknown"


# ---------- Error Info ----------

class ErrorInfo(BaseModel):
    """A single parsed error from test output."""
    file: str = Field(default="unknown", description="File path of the error")
    line_number: int = Field(default=0, description="Line number of the error")
    bug_type: str = Field(default="SYNTAX", description="Error category")
    message: str = Field(default="", description="Error message")
    code_snippet: str = ""

    def model_post_init(self, __context) -> None:
        """Sanitize fields after init — handle None from AI agents."""
        if self.file is None:
            object.__setattr__(self, 'file', 'unknown')
        if self.line_number is None:
            object.__setattr__(self, 'line_number', 0)
        # Normalize bug_type to valid category
        valid = {"LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"}
        bt = str(self.bug_type).upper().strip()
        if bt not in valid:
            bt = "SYNTAX"
        object.__setattr__(self, 'bug_type', bt)
