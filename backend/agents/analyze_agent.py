"""
RIFT 2026 — Analyze Agent  (v2 — "Scan & Trace" approach)

NEW APPROACH:
  1. py_compile every .py file in the repo to find ALL syntax errors directly
  2. Parse test output for runtime errors (NameError, TypeError, etc.)
  3. For NameErrors / ImportErrors, trace through imports to the real source
  4. Deduplicate and return the combined list

This replaces the old regex-only approach which couldn't trace errors to their
actual root cause file.
"""
import logging
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path

from models import BugType, ErrorInfo

logger = logging.getLogger("rift.analyze_agent")


class AnalyzeAgent:
    """Agent that finds ALL errors in a repo — syntax scan + test output parsing."""

    def run(
        self, stdout: str, stderr: str, framework: str, repo_path: str
    ) -> list[ErrorInfo]:
        """
        Analyze the repo for errors using a multi-strategy approach.

        Strategy 1: py_compile scan (catches ALL syntax errors instantly)
        Strategy 2: Parse test output for runtime errors
        Strategy 3: Trace NameErrors/ImportErrors to their root cause
        """
        errors: list[ErrorInfo] = []
        seen = set()  # (file, line_number) dedup

        # ========== STRATEGY 1: py_compile every .py file ==========
        syntax_errors = self._scan_all_syntax(repo_path)
        for err in syntax_errors:
            key = (err.file, err.line_number)
            if key not in seen:
                seen.add(key)
                errors.append(err)
                logger.info(f"  [SCAN] {err.bug_type}: {err.file}:{err.line_number} — {err.message[:80]}")

        # ========== STRATEGY 2: Parse test output for runtime errors ==========
        combined = stdout + "\n" + stderr
        is_python = framework in ("pytest", "unittest", "unknown")

        if is_python:
            runtime_errors = self._parse_pytest_output(combined, repo_path)
        else:
            runtime_errors = self._parse_js_output(combined, repo_path)

        for err in runtime_errors:
            key = (err.file, err.line_number)
            if key not in seen:
                seen.add(key)
                errors.append(err)
                logger.info(f"  [TEST] {err.bug_type}: {err.file}:{err.line_number} — {err.message[:80]}")

        # ========== STRATEGY 3: Trace NameError / ImportError to root cause ==========
        traced_errors = []
        for err in list(errors):
            root = self._trace_to_root_cause(err, repo_path, seen)
            if root and (root.file, root.line_number) not in seen:
                seen.add((root.file, root.line_number))
                traced_errors.append(root)
                logger.info(f"  [TRACE] {root.bug_type}: {root.file}:{root.line_number} — {root.message[:80]}")

        # ========== STRATEGY 4: Lint scan (unused imports) ==========
        lint_errors = self._scan_unused_imports(repo_path)
        for err in lint_errors:
            key = (err.file, err.line_number)
            if key not in seen:
                seen.add(key)
                errors.append(err)
                logger.info(f"  [LINT] {err.bug_type}: {err.file}:{err.line_number} — {err.message[:80]}")

        # Put traced (root cause) errors FIRST so they get fixed first
        final = traced_errors + errors

        logger.info(f"Analyze complete: {len(final)} total error(s)")
        return final

    # ==================== STRATEGY 1: Full syntax scan ====================

    def _scan_all_syntax(self, repo_path: str) -> list[ErrorInfo]:
        """py_compile every .py file in the repo tree."""
        errors = []
        repo = Path(repo_path)

        for py_file in repo.rglob("*.py"):
            # Skip hidden dirs, __pycache__, venv, node_modules
            parts = py_file.relative_to(repo).parts
            if any(p.startswith(".") or p in ("__pycache__", "venv", ".venv", "node_modules", ".git") for p in parts):
                continue

            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                line_num = self._extract_line_from_compile_error(e)
                rel_path = str(py_file.relative_to(repo)).replace("\\", "/")
                snippet = self._read_snippet(py_file, line_num)

                # Extract the actual error message
                err_str = str(e)
                msg = self._clean_compile_error_msg(err_str)

                # Subclassify: indentation vs syntax
                bug_type = BugType.SYNTAX
                if "indent" in msg.lower() or "IndentationError" in err_str:
                    bug_type = BugType.INDENTATION
                elif "TabError" in err_str:
                    bug_type = BugType.INDENTATION

                errors.append(ErrorInfo(
                    file=rel_path,
                    line_number=line_num,
                    bug_type=bug_type,
                    message=msg,
                    code_snippet=snippet,
                ))
            except Exception:
                pass  # Ignore files that can't be read

        return errors

    def _extract_line_from_compile_error(self, e: py_compile.PyCompileError) -> int:
        """Extract line number from a PyCompileError."""
        if hasattr(e, 'exc_value') and hasattr(e.exc_value, 'lineno') and e.exc_value.lineno:
            return e.exc_value.lineno
        match = re.search(r'line\s+(\d+)', str(e))
        return int(match.group(1)) if match else 1

    def _clean_compile_error_msg(self, err_str: str) -> str:
        """Extract a clean error message from PyCompileError string."""
        match = re.search(r'((?:Syntax|Indentation|Tab)Error:\s*.+?)(?:\s*\(|$)', err_str)
        if match:
            return match.group(1).strip()
        lines = err_str.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("File") and not line.startswith("Sorry"):
                return line
        return "SyntaxError"

    # ==================== STRATEGY 2: Test output parsing ====================

    def _parse_pytest_output(self, text: str, repo_path: str) -> list[ErrorInfo]:
        """Parse pytest output for runtime errors (not syntax — those are caught by scan)."""
        errors = []

        # Pattern 1: pytest FAILURES block
        failure_blocks = re.split(r'_{5,}\s+(\w+)\s+_{5,}', text)

        for block in failure_blocks:
            # Find error lines (E   ErrorType: message)
            err_match = re.search(r'E\s+(\w+(?:Error|Exception)):\s*(.+)', block)
            
            # Also catch bare assertion failures: "E       assert 120 == 80"
            assert_match = None
            if not err_match:
                assert_match = re.search(r'E\s+(assert\s+.+)', block)
            
            if not err_match and not assert_match:
                continue

            if err_match:
                err_type = err_match.group(1)
                err_msg = err_match.group(2).strip()
                full_msg = f"{err_type}: {err_msg}"
            else:
                err_type = "AssertionError"
                err_msg = assert_match.group(1).strip()
                full_msg = f"AssertionError: {err_msg}"

            # Skip SyntaxError — already caught by py_compile scan
            # BUT: if py_compile missed it (e.g. dynamic exec), we MUST catch it here.
            # The 'seen' set logic handles dedup if py_compile already caught it.
            pass

            # Find file:line references
            frame_refs = re.findall(r'([\w\\/._-]+\.py):(\d+):', block)
            if not frame_refs:
                continue

            # Use the LAST file:line before the E line (deepest frame)
            file_path, line_num = frame_refs[-1]
            file_path = file_path.replace("\\", "/")
            line_num = int(line_num)

            file_path = self._relativize(file_path, repo_path)

            if "site-packages" in file_path or "lib/python" in file_path.lower():
                continue

            bug_type = self._classify_runtime_error(err_type, full_msg)

            errors.append(ErrorInfo(
                file=file_path,
                line_number=line_num,
                bug_type=bug_type,
                message=full_msg,
                code_snippet=self._read_snippet(Path(repo_path) / file_path, line_num),
            ))

        # Pattern 2: Short summary — FAILED tests/file.py::test - Error: msg
        if not errors:
            for match in re.finditer(
                r'FAILED\s+([\w/\\._-]+\.py)::\w+\s*-\s*(\w+(?:Error|Exception)):\s*(.+)',
                text
            ):
                file_path = match.group(1).replace("\\", "/")
                err_type = match.group(2)
                err_msg = match.group(3).strip()

                # if err_type in ("SyntaxError", "IndentationError"):
                #     continue

                file_path = self._relativize(file_path, repo_path)
                bug_type = self._classify_runtime_error(err_type, f"{err_type}: {err_msg}")

                errors.append(ErrorInfo(
                    file=file_path,
                    line_number=0,
                    bug_type=bug_type,
                    message=f"{err_type}: {err_msg}",
                    code_snippet="",
                ))

        # Pattern 3: Generic Python traceback (File "X", line N)
        if not errors:
            for match in re.finditer(
                r'File\s+"([^"]+)",\s+line\s+(\d+).*?\n\s*(\w+(?:Error|Exception)):\s*(.+)',
                text, re.DOTALL
            ):
                file_path = match.group(1).replace("\\", "/")
                line_num = int(match.group(2))
                err_type = match.group(3)
                err_msg = match.group(4).strip()

                if "site-packages" in file_path:
                    continue
                # if err_type in ("SyntaxError", "IndentationError"):
                #     continue

                file_path = self._relativize(file_path, repo_path)
                bug_type = self._classify_runtime_error(err_type, f"{err_type}: {err_msg}")

                errors.append(ErrorInfo(
                    file=file_path,
                    line_number=line_num,
                    bug_type=bug_type,
                    message=f"{err_type}: {err_msg}",
                    code_snippet="",
                ))

        return errors

    def _parse_js_output(self, text: str, repo_path: str) -> list[ErrorInfo]:
        """Parse Jest/Mocha output for JavaScript errors."""
        errors = []

        for match in re.finditer(r'at\s+(?:\S+\s+\()?([\w/\\._-]+\.(?:js|ts|jsx|tsx)):(\d+):\d+', text):
            file_path = match.group(1).replace("\\", "/")
            line_num = int(match.group(2))
            if "node_modules" in file_path:
                continue
            errors.append(ErrorInfo(
                file=file_path, line_number=line_num,
                bug_type=BugType.LOGIC, message="Test failure",
            ))

        for match in re.finditer(r'([\w/\\._-]+\.(?:js|ts)):(\d+):\d+:\s*(.+)', text):
            file_path = match.group(1).replace("\\", "/")
            line_num = int(match.group(2))
            msg = match.group(3)
            errors.append(ErrorInfo(
                file=file_path, line_number=line_num,
                bug_type=BugType.LINTING, message=msg,
            ))

        return errors

    def _classify_runtime_error(self, err_type: str, msg: str) -> str:
        """Classify a runtime error into a BugType string."""
        mapping = {
            "NameError": BugType.IMPORT,
            "ImportError": BugType.IMPORT,
            "ModuleNotFoundError": BugType.IMPORT,
            "TypeError": BugType.TYPE_ERROR,
            "ValueError": BugType.LOGIC,
            "AssertionError": BugType.LOGIC,
            "AttributeError": BugType.LOGIC,
            "KeyError": BugType.LOGIC,
            "IndexError": BugType.LOGIC,
            "ZeroDivisionError": BugType.LOGIC,
            "SyntaxError": BugType.SYNTAX,
            "IndentationError": BugType.INDENTATION,
        }
        return mapping.get(err_type, BugType.LOGIC)

    # ==================== STRATEGY 3: Root cause tracing ====================

    def _trace_to_root_cause(
        self, err: ErrorInfo, repo_path: str, seen: set
    ) -> ErrorInfo | None:
        """For NameError/ImportError, trace to the actual broken source file."""

        msg = err.message
        is_name_error = "NameError" in msg
        is_import_error = (
            str(err.bug_type) in ("IMPORT", BugType.IMPORT)
            or "ImportError" in msg
            or "ModuleNotFoundError" in msg
        )

        if not is_name_error and not is_import_error:
            return None

        module_name = None

        if is_name_error:
            name_match = re.search(r"name\s+['\"]?(\w+)['\"]?\s+is not defined", msg)
            if not name_match:
                return None
            undefined_name = name_match.group(1)

            try:
                source = (Path(repo_path) / err.file).read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None

            import_pat = re.compile(
                rf'^\s*(?:import\s+(\S+)\s+as\s+{re.escape(undefined_name)}|'
                rf'from\s+(\S+)\s+import\s+.*\b{re.escape(undefined_name)}\b|'
                rf'import\s+{re.escape(undefined_name)}\b)',
                re.MULTILINE
            )
            m = import_pat.search(source)
            if not m:
                return None
            module_name = m.group(1) or m.group(2) or undefined_name

        elif is_import_error:
            mod_match = re.search(r"(?:No module named|cannot import name)\s+['\"]?(\S+)['\"]?", msg)
            if not mod_match:
                return None
            module_name = mod_match.group(1).strip("'\"")

        if not module_name:
            return None

        source_file = self._resolve_module(module_name, repo_path)
        if not source_file:
            return None

        # Check if this source file has a syntax error
        try:
            py_compile.compile(str(source_file), doraise=True)
            return None  # No syntax error — can't trace further
        except py_compile.PyCompileError as e:
            line_num = self._extract_line_from_compile_error(e)
            rel_path = str(source_file.relative_to(Path(repo_path))).replace("\\", "/")

            # Already found by scan?
            if (rel_path, line_num) in seen:
                return None

            msg_clean = self._clean_compile_error_msg(str(e))
            snippet = self._read_snippet(source_file, line_num)

            bug_type = BugType.SYNTAX
            if "indent" in msg_clean.lower():
                bug_type = BugType.INDENTATION

            return ErrorInfo(
                file=rel_path,
                line_number=line_num,
                bug_type=bug_type,
                message=msg_clean,
                code_snippet=snippet,
            )

    # ==================== STRATEGY 4: Unused import scan ====================

    def _scan_unused_imports(self, repo_path: str) -> list[ErrorInfo]:
        """Scan all .py files for unused imports (LINTING errors)."""
        errors = []
        repo = Path(repo_path)

        for py_file in repo.rglob("*.py"):
            parts = py_file.relative_to(repo).parts
            if any(p.startswith(".") or p in ("__pycache__", "venv", ".venv", "node_modules", ".git") for p in parts):
                continue
            # Skip test files — we only lint source files
            if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
                continue
            # Skip __init__.py — imports there are often re-exports
            if py_file.name == "__init__.py":
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # First check the file compiles — no point linting broken syntax
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError:
                continue

            lines = source.splitlines()
            rel_path = str(py_file.relative_to(repo)).replace("\\", "/")

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                # Match: import X  or  import X as Y
                m_import = re.match(r'^import\s+(\w+)(?:\s+as\s+(\w+))?\s*$', stripped)
                if m_import:
                    module = m_import.group(1)
                    alias = m_import.group(2) or module
                    # Check if the alias is used anywhere else in the file
                    usage_pat = re.compile(r'\b' + re.escape(alias) + r'\b')
                    used = False
                    for j, other_line in enumerate(lines, 1):
                        if j == i:
                            continue
                        ol = other_line.strip()
                        if ol.startswith("#"):
                            continue
                        if usage_pat.search(ol):
                            used = True
                            break
                    if not used:
                        errors.append(ErrorInfo(
                            file=rel_path,
                            line_number=i,
                            bug_type=BugType.LINTING,
                            message=f"Unused import '{module}'",
                            code_snippet=self._read_snippet(py_file, i),
                        ))
                        continue

                # Match: from X import Y, Z
                m_from = re.match(r'^from\s+\S+\s+import\s+(.+)$', stripped)
                if m_from:
                    names_str = m_from.group(1)
                    # Parse individual names (handle 'as' aliases)
                    for part in names_str.split(","):
                        part = part.strip()
                        if not part:
                            continue
                        as_match = re.match(r'(\w+)\s+as\s+(\w+)', part)
                        if as_match:
                            original_name = as_match.group(1)
                            alias = as_match.group(2)
                        else:
                            original_name = part.split()[0]
                            alias = original_name
                        # Check if alias used elsewhere
                        usage_pat = re.compile(r'\b' + re.escape(alias) + r'\b')
                        used = False
                        for j, other_line in enumerate(lines, 1):
                            if j == i:
                                continue
                            ol = other_line.strip()
                            if ol.startswith("#"):
                                continue
                            if usage_pat.search(ol):
                                used = True
                                break
                        if not used:
                            errors.append(ErrorInfo(
                                file=rel_path,
                                line_number=i,
                                bug_type=BugType.LINTING,
                                message=f"Unused import '{original_name}'",
                                code_snippet=self._read_snippet(py_file, i),
                            ))
                            break  # Only report one unused per line

        return errors

    # ==================== Helpers ====================

    def _resolve_module(self, module_name: str, repo_path: str) -> Path | None:
        """Resolve a Python module name to a file path within the repo."""
        parts = module_name.replace(".", "/")
        candidates = [
            Path(repo_path) / f"{parts}.py",
            Path(repo_path) / parts / "__init__.py",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _relativize(self, file_path: str, repo_path: str) -> str:
        """Convert to repo-relative path."""
        try:
            p = Path(file_path)
            r = Path(repo_path)
            if p.is_absolute():
                try:
                    return str(p.relative_to(r)).replace("\\", "/")
                except ValueError:
                    return file_path
            return file_path.replace("\\", "/")
        except Exception:
            return file_path

    def _read_snippet(self, file_path: Path, line_num: int, context: int = 3) -> str:
        """Read source lines around the error."""
        try:
            if not file_path.exists():
                return ""
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(0, line_num - context - 1)
            end = min(len(lines), line_num + context)
            result = []
            for i in range(start, end):
                marker = ">>>" if i == line_num - 1 else "   "
                result.append(f"{marker} {i + 1}: {lines[i]}")
            return "\n".join(result)
        except Exception:
            return ""


# Singleton
analyze_agent = AnalyzeAgent()
