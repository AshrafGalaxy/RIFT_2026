"""
RIFT 2026 — Analyze Agent

Parses test stderr/stdout and classifies each error into one of:
LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION.
"""
import logging
import re
from pathlib import Path

from models import BugType, ErrorInfo

logger = logging.getLogger("rift.analyze_agent")


# --- Error classification patterns ---

PYTHON_PATTERNS: list[tuple[str, BugType, str]] = [
    # Import errors
    (r"(?:ModuleNotFoundError|ImportError):\s+(?:No module named\s+)?['\"]?(\S+)['\"]?",
     BugType.IMPORT, "import"),
    (r"cannot import name\s+['\"](\S+)['\"]",
     BugType.IMPORT, "import"),

    # Syntax errors
    (r"SyntaxError:\s+(.*)",
     BugType.SYNTAX, "syntax"),
    (r"invalid syntax",
     BugType.SYNTAX, "syntax"),

    # Indentation errors
    (r"IndentationError:\s+(.*)",
     BugType.INDENTATION, "indentation"),
    (r"TabError:\s+(.*)",
     BugType.INDENTATION, "indentation"),
    (r"unexpected indent",
     BugType.INDENTATION, "indentation"),

    # Type errors
    (r"TypeError:\s+(.*)",
     BugType.TYPE_ERROR, "type"),
    (r"unsupported operand type",
     BugType.TYPE_ERROR, "type"),

    # Linting
    (r"(E\d{3})\s+",  # PEP8 error codes
     BugType.LINTING, "lint"),
    (r"(W\d{3})\s+",  # PEP8 warnings
     BugType.LINTING, "lint"),
    (r"flake8|pylint|pycodestyle",
     BugType.LINTING, "lint"),

    # Logic errors (assertion failures, wrong results)
    (r"AssertionError:\s*(.*)",
     BugType.LOGIC, "logic"),
    (r"assert\s+.*==.*",
     BugType.LOGIC, "logic"),
    (r"Expected\s+.*but\s+got",
     BugType.LOGIC, "logic"),
    (r"FAILED.*assert",
     BugType.LOGIC, "logic"),
]

JS_PATTERNS: list[tuple[str, BugType, str]] = [
    # Import/require errors
    (r"Cannot find module\s+['\"](\S+)['\"]",
     BugType.IMPORT, "import"),
    (r"is not defined",
     BugType.IMPORT, "import"),
    (r"Module not found",
     BugType.IMPORT, "import"),

    # Syntax errors
    (r"SyntaxError:\s+(.*)",
     BugType.SYNTAX, "syntax"),
    (r"Unexpected token",
     BugType.SYNTAX, "syntax"),

    # Type errors
    (r"TypeError:\s+(.*)",
     BugType.TYPE_ERROR, "type"),
    (r"is not a function",
     BugType.TYPE_ERROR, "type"),
    (r"Cannot read propert",
     BugType.TYPE_ERROR, "type"),

    # Linting (ESLint)
    (r"eslint|no-unused-vars|no-undef|semi|indent",
     BugType.LINTING, "lint"),

    # Logic (test assertion failures)
    (r"expect\(.*\)\.to",
     BugType.LOGIC, "logic"),
    (r"Expected.*to\s+(equal|be|match|deep)",
     BugType.LOGIC, "logic"),
    (r"AssertionError",
     BugType.LOGIC, "logic"),
]


class AnalyzeAgent:
    """Agent that parses test output and classifies errors."""

    def run(
        self, stdout: str, stderr: str, framework: str, repo_path: str
    ) -> list[ErrorInfo]:
        """
        Analyze combined test output and return classified errors.

        Args:
            stdout: Test stdout.
            stderr: Test stderr.
            framework: Detected test framework (pytest, jest, etc.)
            repo_path: Path to the repo (for reading source files).

        Returns:
            List of ErrorInfo objects.
        """
        combined = stdout + "\n" + stderr
        errors: list[ErrorInfo] = []
        seen = set()  # Deduplicate by (file, line)

        is_python = framework in ("pytest", "unittest")
        patterns = PYTHON_PATTERNS if is_python else JS_PATTERNS

        # --- Extract file:line references from output ---
        file_line_errors = self._extract_file_line_refs(
            combined, is_python, repo_path
        )

        for file_path, line_num, error_msg in file_line_errors:
            key = (file_path, line_num)
            if key in seen:
                continue
            seen.add(key)

            bug_type = self._classify_error(error_msg, patterns)
            snippet = self._read_code_snippet(repo_path, file_path, line_num)

            errors.append(
                ErrorInfo(
                    file=file_path,
                    line_number=line_num,
                    bug_type=bug_type,
                    message=error_msg.strip(),
                    code_snippet=snippet,
                )
            )

        # If no file references found, try to classify from raw output
        if not errors:
            errors = self._fallback_classify(combined, patterns, repo_path)

        logger.info(f"Analyzed output: found {len(errors)} error(s)")
        for err in errors:
            logger.info(f"  {err.bug_type}: {err.file}:{err.line_number} — {err.message[:80]}")

        return errors

    def _extract_file_line_refs(
        self, text: str, is_python: bool, repo_path: str
    ) -> list[tuple[str, int, str]]:
        """Extract (file, line_number, error_message) from test output."""
        results = []

        if is_python:
            # Python tracebacks: File "path/to/file.py", line N
            pattern = r'File\s+"([^"]+)",\s+line\s+(\d+)(?:.*\n\s+.*\n(\S.*))?'
            for match in re.finditer(pattern, text):
                file_path = match.group(1)
                line_num = int(match.group(2))
                error_msg = match.group(3) or ""
                file_path = self._relativize(file_path, repo_path)
                if file_path and not file_path.startswith("<"):
                    results.append((file_path, line_num, error_msg))

            # Pytest short format: file.py:line: ErrorType: msg
            pattern2 = r"(\S+\.py):(\d+):\s*(.*Error.*)"
            for match in re.finditer(pattern2, text):
                file_path = match.group(1)
                line_num = int(match.group(2))
                error_msg = match.group(3)
                file_path = self._relativize(file_path, repo_path)
                results.append((file_path, line_num, error_msg))

        else:
            # JavaScript: at path/to/file.js:line:col
            pattern = r"at\s+(?:\S+\s+\()?(\S+\.(?:js|ts|jsx|tsx)):(\d+):\d+"
            for match in re.finditer(pattern, text):
                file_path = match.group(1)
                line_num = int(match.group(2))
                results.append((file_path, line_num, ""))

            # ESLint or generic: file.js:line:col: error msg
            pattern2 = r"(\S+\.(?:js|ts|jsx|tsx)):(\d+):\d+:\s*(.*)"
            for match in re.finditer(pattern2, text):
                file_path = match.group(1)
                line_num = int(match.group(2))
                error_msg = match.group(3)
                results.append((file_path, line_num, error_msg))

        return results

    def _classify_error(
        self, error_msg: str, patterns: list[tuple[str, BugType, str]]
    ) -> BugType:
        """Classify an error message into a BugType."""
        for pattern, bug_type, _ in patterns:
            if re.search(pattern, error_msg, re.IGNORECASE):
                return bug_type
        return BugType.LOGIC  # default fallback

    def _fallback_classify(
        self, text: str, patterns: list[tuple[str, BugType, str]], repo_path: str
    ) -> list[ErrorInfo]:
        """When no file:line refs found, try to classify errors from raw text."""
        errors = []
        for pattern, bug_type, _ in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                errors.append(
                    ErrorInfo(
                        file="unknown",
                        line_number=0,
                        bug_type=bug_type,
                        message=match.group(0).strip()[:200],
                        code_snippet="",
                    )
                )
                if len(errors) >= 10:
                    break
            if len(errors) >= 10:
                break
        return errors

    def _relativize(self, file_path: str, repo_path: str) -> str:
        """Convert absolute path to relative within the repo."""
        try:
            p = Path(file_path)
            r = Path(repo_path)
            if p.is_absolute():
                try:
                    return str(p.relative_to(r))
                except ValueError:
                    return str(p.name)
            return file_path
        except Exception:
            return file_path

    def _read_code_snippet(
        self, repo_path: str, file_path: str, line_num: int, context: int = 3
    ) -> str:
        """Read a few lines around the error from the source file."""
        try:
            full_path = Path(repo_path) / file_path
            if not full_path.exists():
                return ""

            lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(0, line_num - context - 1)
            end = min(len(lines), line_num + context)
            snippet_lines = []
            for i in range(start, end):
                marker = ">>>" if i == line_num - 1 else "   "
                snippet_lines.append(f"{marker} {i + 1}: {lines[i]}")
            return "\n".join(snippet_lines)
        except Exception:
            return ""


# Singleton
analyze_agent = AnalyzeAgent()
