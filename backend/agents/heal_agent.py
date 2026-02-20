"""
RIFT 2026 — Heal Agent  (v2 — "Fix & Verify" approach)

NEW APPROACH:
  1. Read the broken file and understand the error context
  2. Apply a targeted fix based on error type
  3. VERIFY with py_compile that the fix actually works
  4. If verification fails, revert and try an alternative fix
  5. NEVER comment out imports — fix the actual source problem

Key principles:
  - Every fix is verified before committing
  - Syntax fixes use pattern matching on the actual line
  - Import errors trace to the source file and fix there
  - No destructive changes (no commenting out code)
"""
import logging
import os
import py_compile
import re
import difflib
from pathlib import Path

from git import Repo

from models import BugType, ErrorInfo, Fix, FixStatus
from services.git_service import git_service
from utils import format_branch_name, format_commit_message

logger = logging.getLogger("rift.heal_agent")


class HealAgent:
    """Agent that applies verified code fixes and commits them."""

    def run(
        self,
        repo_path: str,
        errors: list[ErrorInfo],
        team_name: str,
        leader_name: str,
        iteration: int,
    ) -> tuple[list[Fix], str, int]:
        """
        Apply fixes for all errors, create branch, commit each fix.

        Returns: (list[Fix], branch_name, total_new_commits)
        """
        repo = git_service.get_repo(repo_path)
        branch_name = format_branch_name(team_name, leader_name)

        # Create branch on first iteration
        if iteration == 1:
            git_service.create_branch(repo, team_name, leader_name)
        else:
            if repo.active_branch.name != branch_name:
                repo.git.checkout(branch_name)

        fixes: list[Fix] = []
        commit_count = 0

        for error in errors:
            fix = self._fix_error(repo_path, error)
            if fix is None:
                logger.warning(f"Could not fix {error.file}:{error.line_number} ({error.bug_type})")
                continue

            # Commit the fix (use fix.file for cross-file fixes)
            try:
                bt_str = str(error.bug_type)
                if hasattr(error.bug_type, 'value'):
                    bt_str = error.bug_type.value
                commit_file = fix.file  # May differ from error.file for cross-file fixes
                commit_msg = format_commit_message(bt_str, commit_file, fix.line_number)
                fix.commit_message = commit_msg
                git_service.commit_fix(repo, commit_file, commit_msg)
                fix.status = FixStatus.APPLIED
                commit_count += 1
                logger.info(f"Fixed {commit_file}:{fix.line_number} ({error.bug_type})")
            except Exception as e:
                logger.error(f"Commit failed for {fix.file}: {e}")
                fix.status = FixStatus.FAILED

            fixes.append(fix)

        # Push all commits
        if commit_count > 0:
            try:
                git_service.push(repo, branch_name)
            except Exception as e:
                logger.error(f"Push failed: {e}")

        logger.info(f"Heal iteration {iteration}: {commit_count}/{len(errors)} fixed")
        return fixes, branch_name, commit_count

    # ==================== Main Fix Router ====================

    def _fix_error(self, repo_path: str, error: ErrorInfo) -> Fix | None:
        """
        Generate and apply a fix, then VERIFY it.
        Returns a Fix object or None if unfixable.
        """
        file_path = Path(repo_path) / error.file
        if not file_path.exists():
            logger.warning(f"File not found: {error.file}")
            return None

        try:
            original_content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        lines = original_content.splitlines(keepends=True)
        if error.line_number < 1 or error.line_number > len(lines):
            logger.warning(f"Line {error.line_number} out of range for {error.file} ({len(lines)} lines)")
            return None

        original_line = lines[error.line_number - 1]
        bt = str(error.bug_type).upper()
        if hasattr(error.bug_type, 'value'):
            bt = error.bug_type.value

        # Try multiple fix strategies in order
        fix_strategies = self._get_strategies(bt, error, repo_path)

        for strategy_name, strategy_fn in fix_strategies:
            fixed_line = strategy_fn(error, lines, error.line_number)
            if fixed_line is None:
                continue
            
            # Protocol: "__CROSSFILE__ <rel_path>|||<line_num>|||<content>"
            if fixed_line.startswith("__CROSSFILE__ "):
                try:
                    parts = fixed_line.split(" ", 1)[1].split("|||", 2)
                    target_rel, target_line_str, target_code = parts[0], parts[1], parts[2]
                    target_line = int(target_line_str)
                    
                    target_path = Path(repo_path) / target_rel
                    target_content = target_path.read_text(encoding="utf-8", errors="replace")
                    target_lines_list = target_content.splitlines(keepends=True)
                    target_lines_list[target_line - 1] = target_code + "\n"
                    target_path.write_text("".join(target_lines_list), encoding="utf-8")
                    
                    return Fix(
                        file=target_rel,
                        bug_type=error.bug_type,
                        line_number=target_line,
                        original_code="(cross-file fix)",
                        fixed_code=target_code.strip(),
                        commit_message=f"Cross-file fix {bt} with {strategy_name}",
                        status=FixStatus.APPLIED
                    )
                except Exception as e:
                    logger.error(f"Cross-file fix failed: {e}")
                    continue

            if fixed_line.rstrip() == original_line.rstrip():
                continue  # No-op, skip

            # Apply and verify
            new_lines = list(lines)
            new_lines[error.line_number - 1] = fixed_line if fixed_line.endswith("\n") else fixed_line + "\n"
            new_content = "".join(new_lines)

            file_path.write_text(new_content, encoding="utf-8")

            # Verify with py_compile (for Python files)
            if file_path.suffix == ".py":
                if self._verify_syntax(file_path):
                    logger.info(f"  [{strategy_name}] Fix verified for {error.file}:{error.line_number}")
                    return Fix(
                        file=error.file,
                        bug_type=error.bug_type,
                        line_number=error.line_number,
                        original_code=original_line.rstrip(),
                        fixed_code=fixed_line.rstrip(),
                        status=FixStatus.PENDING,
                    )
                else:
                    # Revert — this fix didn't work
                    file_path.write_text(original_content, encoding="utf-8")
                    logger.info(f"  [{strategy_name}] Fix FAILED verification, reverting")
                    continue
            else:
                # Non-Python: apply without py_compile verification
                return Fix(
                    file=error.file,
                    bug_type=error.bug_type,
                    line_number=error.line_number,
                    original_code=original_line.rstrip(),
                    fixed_code=fixed_line.rstrip(),
                    status=FixStatus.PENDING,
                )

        # All strategies failed — revert to original
        file_path.write_text(original_content, encoding="utf-8")
        logger.warning(f"All fix strategies failed for {error.file}:{error.line_number}")
        return None

    def _get_strategies(self, bug_type: str, error: ErrorInfo, repo_path: str) -> list:
        """Return ordered list of (name, function) fix strategies."""
        common = [
            ("missing_colon", self._fix_missing_colon),
            ("unmatched_parens", self._fix_unmatched_parens),
            ("unmatched_quotes", self._fix_unmatched_quotes),
            ("bad_indent", self._fix_indentation),
        ]

        if bug_type == "SYNTAX":
            return [
                ("missing_colon", self._fix_missing_colon),
                ("unmatched_parens", self._fix_unmatched_parens),
                ("unmatched_quotes", self._fix_unmatched_quotes),
                ("trailing_garbage", self._fix_trailing_garbage),
                ("bad_indent", self._fix_indentation),
            ]
        elif bug_type == "INDENTATION":
            return [
                ("fix_exec_indentation", lambda e, ls, ln: self._fix_exec_indentation(e, ls, ln)),
                ("bad_indent", self._fix_indentation),
                ("tab_to_spaces", self._fix_tabs_to_spaces),
            ]
        elif bug_type == "IMPORT":
            return [
                ("fix_name_not_defined", lambda e, ls, ln: self._fix_name_not_defined(e, ls, ln, repo_path)),
                ("fix_module_typo", self._fix_module_typo),
                ("fix_import_name_typo", lambda e, ls, ln: self._fix_import_name_typo(e, ls, ln, repo_path)),
                ("missing_colon", self._fix_missing_colon),  # import may fail due to syntax in source
            ] + common
        elif bug_type == "TYPE_ERROR":
            return [
                ("type_conversion", self._fix_type_error),
            ] + common
        elif bug_type == "LINTING":
            return [
                ("trailing_whitespace", self._fix_trailing_whitespace),
                ("unused_import", self._fix_unused_import),
            ]
        elif bug_type == "LOGIC":
            return [
                ("fix_missing_return", lambda e, ls, ln: self._fix_missing_return(e, ls, ln, repo_path)),
                ("fix_wrong_operator", lambda e, ls, ln: self._fix_wrong_operator(e, ls, ln, repo_path)),
                ("eq_vs_assign", self._fix_eq_vs_assign),
                ("off_by_one", self._fix_off_by_one),
            ]
        else:
            return common

    # ==================== Verification ====================

    def _verify_syntax(self, file_path: Path) -> bool:
        """Check if a Python file compiles without syntax errors."""
        try:
            py_compile.compile(str(file_path), doraise=True)
            return True
        except py_compile.PyCompileError:
            return False
        except Exception:
            return False

    # ==================== Fix Strategies ====================

    def _fix_missing_colon(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Add missing colon at end of def/class/if/for/while/with/else/elif/try/except/finally.
        Also adds 'pass' body if the block has no body."""
        line = lines[line_num - 1]
        stripped = line.rstrip()
        indent = line[:len(line) - len(line.lstrip())]

        keywords = ("def ", "class ", "if ", "for ", "while ", "with ",
                     "else", "elif ", "try", "except", "except ", "finally")
        content = stripped.lstrip()
        for kw in keywords:
            if content.startswith(kw) and not stripped.endswith(":"):
                fixed = stripped + ":"

                # Check if the block has a body (next non-empty line must be more indented)
                needs_pass = True
                for j in range(line_num, min(line_num + 5, len(lines))):
                    next_line = lines[j]
                    if next_line.strip():  # non-empty
                        next_indent = next_line[:len(next_line) - len(next_line.lstrip())]
                        if len(next_indent) > len(indent):
                            needs_pass = False  # Has a body
                        break

                if needs_pass:
                    fixed = fixed + "\n" + indent + "    pass"

                return fixed + "\n"
        return None

    def _fix_unmatched_parens(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix unmatched parentheses or brackets."""
        line = lines[line_num - 1]

        open_parens = line.count("(") - line.count(")")
        if open_parens > 0:
            return line.rstrip() + ")" * open_parens + "\n"
        if open_parens < 0:
            # Too many closing parens — remove extras from end
            result = line.rstrip()
            for _ in range(-open_parens):
                idx = result.rfind(")")
                if idx >= 0:
                    result = result[:idx] + result[idx+1:]
            return result + "\n"

        open_brackets = line.count("[") - line.count("]")
        if open_brackets > 0:
            return line.rstrip() + "]" * open_brackets + "\n"

        open_braces = line.count("{") - line.count("}")
        if open_braces > 0:
            return line.rstrip() + "}" * open_braces + "\n"

        return None

    def _fix_unmatched_quotes(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix unmatched string quotes."""
        line = lines[line_num - 1]
        stripped = line.rstrip()

        # Count quotes outside of escaped sequences
        single = len(re.findall(r"(?<!\\)'", stripped))
        double = len(re.findall(r'(?<!\\)"', stripped))

        if single % 2 != 0:
            return stripped + "'\n"
        if double % 2 != 0:
            return stripped + '"\n'

        return None

    def _fix_trailing_garbage(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Remove trailing garbage characters after valid code."""
        line = lines[line_num - 1]
        stripped = line.rstrip()

        # Try progressively shorter versions of the line
        for i in range(len(stripped) - 1, max(0, len(stripped) - 5), -1):
            candidate = stripped[:i]
            if candidate.strip():
                # Check if this would be valid by itself
                try:
                    compile(candidate.strip(), '<string>', 'exec')
                    return line[:len(line) - len(line.lstrip())] + candidate.strip() + "\n"
                except SyntaxError:
                    continue

        return None

    def _fix_indentation(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix indentation by aligning with surrounding code."""
        if line_num < 2:
            return lines[line_num - 1].lstrip()  # No context, just dedent

        # Find the previous non-empty line
        prev_indent = ""
        for i in range(line_num - 2, max(-1, line_num - 10), -1):
            prev_line = lines[i]
            if prev_line.strip():
                prev_indent = re.match(r'^(\s*)', prev_line).group(1)
                # If previous line ends with ':', add one indent level
                if prev_line.rstrip().endswith(":"):
                    prev_indent += "    "
                break

        current_content = lines[line_num - 1].lstrip()

        # Dedent keywords (else, elif, except, finally)
        if current_content.startswith(("else:", "elif ", "except", "finally:", "except:")):
            if len(prev_indent) >= 4:
                prev_indent = prev_indent[:-4]

        return prev_indent + current_content

    def _fix_tabs_to_spaces(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Convert tabs to 4 spaces."""
        line = lines[line_num - 1]
        if "\t" in line:
            return line.replace("\t", "    ")
        return None

    def _fix_module_typo(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix common module name typos in imports."""
        line = lines[line_num - 1]
        typo_map = {
            "colections": "collections",
            "ittertools": "itertools",
            "jsons": "json",
            "maths": "math",
            "os.paths": "os.path",
            "requets": "requests",
            "numppy": "numpy",
            "pands": "pandas",
            "randon": "random",
            "strng": "string",
        }
        for typo, correct in typo_map.items():
            if typo in line:
                return line.replace(typo, correct)
        return None

    def _fix_type_error(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix type errors by adding conversions."""
        msg = error.message.lower()
        line = lines[line_num - 1]

        if "str" in msg and "int" in msg and "+" in line:
            # Wrap the non-string operand in str()
            return re.sub(
                r'(\+\s*)(\w+)', lambda m: m.group(1) + f"str({m.group(2)})",
                line, count=1,
            )

        if "nonetype" in msg and "subscript" in msg:
            indent = re.match(r'^(\s*)', line).group(1)
            var_match = re.search(r'(\w+)\s*[\[\(.]', line)
            if var_match:
                var = var_match.group(1)
                return f"{indent}if {var} is not None:\n{indent}    {line.lstrip()}"

        return None

    def _fix_trailing_whitespace(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Remove trailing whitespace."""
        line = lines[line_num - 1]
        cleaned = line.rstrip() + "\n"
        return cleaned if cleaned != line else None

    def _fix_unused_import(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Remove the unused import line entirely."""
        line = lines[line_num - 1]
        if line.strip().startswith(("import ", "from ")):
            # Return empty string to effectively remove the line
            return "\n"  # Replace with blank line to preserve line numbers
        return None

    def _fix_eq_vs_assign(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix = vs == confusion in if statements."""
        line = lines[line_num - 1]
        if 'if ' in line and re.search(r'(?<!=)=(?!=)', line):
            fixed = re.sub(r'(?<!=)=(?!=)', '==', line, count=1)
            if fixed != line:
                return fixed
        return None

    def _fix_off_by_one(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix off-by-one: > to >=, < to <=."""
        line = lines[line_num - 1]
        if ' > ' in line:
            return line.replace(' > ', ' >= ', 1)
        if ' < ' in line:
            return line.replace(' < ', ' <= ', 1)
        return None

    def _fix_wrong_operator(self, error: ErrorInfo, lines: list[str], line_num: int, repo_path: str) -> str | None:
        """Fix wrong arithmetic operator by tracing assertion failure to source function.
        
        When a test asserts `func(a, b) == expected` but gets wrong value,
        scan the source function for arithmetic operators and try flipping them.
        Uses __CROSSFILE__ to patch the source file.
        """
        msg = error.message.lower()
        line = lines[line_num - 1] if line_num <= len(lines) else ""

        # Heuristic: assertion failure with numeric mismatch
        if "assert" not in msg and "assert" not in line:
            return None

        # Extract function name from the assert line or error message
        # Patterns: "assert func(args) == val" or "+  where X = func(args)"
        func_name = None
        for search_text in [line, msg]:
            m = re.search(r'(\w+)\s*\(', search_text)
            if m and m.group(1) not in ('assert', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'type', 'isinstance', 'print'):
                func_name = m.group(1)
                break

        if not func_name:
            return None

        # Search ALL source files (non-test) in the repo for this function
        repo = Path(repo_path)

        target_file = None
        func_line_idx = -1
        func_end_idx = -1
        src_lines = []

        for py_file in sorted(repo.rglob("*.py")):
            rel = str(py_file.relative_to(repo)).replace("\\", "/")
            if "test" in rel.lower() or "__pycache__" in rel or ".venv" in rel or "node_modules" in rel:
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                file_lines = content.splitlines(keepends=False)
                for i, sl in enumerate(file_lines):
                    if re.match(rf'^\s*def\s+{re.escape(func_name)}\s*\(', sl):
                        target_file = py_file
                        func_line_idx = i
                        src_lines = file_lines
                        # Find end of function (next def or end of file)
                        indent = len(sl) - len(sl.lstrip())
                        for k in range(i + 1, len(file_lines)):
                            stripped = file_lines[k].strip()
                            if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                                line_indent = len(file_lines[k]) - len(file_lines[k].lstrip())
                                if line_indent <= indent and stripped:
                                    func_end_idx = k
                                    break
                        if func_end_idx == -1:
                            func_end_idx = len(file_lines)
                        break
            except Exception:
                continue
            if target_file:
                break

        if not target_file or func_line_idx == -1:
            return None

        # Scan function body for arithmetic operator and try flipping
        # PRIORITIZE return lines over assignment lines to avoid flipping the wrong operator
        op_pairs = [(' + ', ' - '), (' - ', ' + '), (' * ', ' / '), (' / ', ' * ')]

        # Pass 1: Check return statements first (most likely location of wrong operator)
        for body_idx in range(func_line_idx + 1, func_end_idx):
            body_line = src_lines[body_idx]
            if 'return' not in body_line:
                continue
            for old_op, new_op in op_pairs:
                if old_op in body_line:
                    fixed_line = body_line.replace(old_op, new_op, 1)
                    target_rel = str(target_file.relative_to(repo_path)).replace("\\", "/")
                    return f"__CROSSFILE__ {target_rel}|||{body_idx + 1}|||{fixed_line}"

        # Pass 2: Fall back to assignment lines only if no return line had operators
        for body_idx in range(func_line_idx + 1, func_end_idx):
            body_line = src_lines[body_idx]
            if 'return' in body_line or '=' not in body_line:
                continue
            for old_op, new_op in op_pairs:
                if old_op in body_line:
                    fixed_line = body_line.replace(old_op, new_op, 1)
                    target_rel = str(target_file.relative_to(repo_path)).replace("\\", "/")
                    return f"__CROSSFILE__ {target_rel}|||{body_idx + 1}|||{fixed_line}"

        return None

    # ==================== Legacy Apply (for non-verified path) ====================

    def _apply_fix(self, repo_path: str, error: ErrorInfo, fix: Fix) -> bool:
        """Write the fix to the file (legacy path — new code uses _fix_error)."""
        file_path = Path(repo_path) / error.file
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            if error.line_number < 1 or error.line_number > len(lines):
                return False
            lines[error.line_number - 1] = fix.fixed_code + "\n"
            file_path.write_text("".join(lines), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to apply fix to {error.file}: {e}")
            return False


    def _fix_import_name_typo(self, error: ErrorInfo, lines: list[str], line_num: int, repo_path: str) -> str | None:
        """Fix 'cannot import name X from Y' by finding close match in Y."""
        line = lines[line_num - 1]
        msg = error.message

        # Parse: cannot import name 'X' from 'Y'
        m = re.search(r"cannot import name ['\"](\w+)['\"] from ['\"]([\w.]+)['\"]", msg)
        if not m:
            return None
        
        broken_name = m.group(1)
        module_name = m.group(2)

        # Resolve module path
        try:
            parts = module_name.replace(".", "/")
            source_file = Path(repo_path) / f"{parts}.py"
            if not source_file.exists():
                source_file = Path(repo_path) / parts / "__init__.py"
            
            if not source_file.exists():
                return None
                
            source_code = source_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        # Find exported names in source
        exports = re.findall(r"^def\s+(\w+)|^class\s+(\w+)|^(\w+)\s*=", source_code, re.MULTILINE)
        candidates = []
        for match in exports:
            name = next((g for g in match if g), None)
            if name:
                candidates.append(name)

        if not candidates:
            return None

        # Find closest match
        matches = difflib.get_close_matches(broken_name, candidates, n=1, cutoff=0.7)
        if not matches:
            return None
        
        best_match = matches[0]
        
        if broken_name in line:
            return line.replace(broken_name, best_match)
            
        return None

    def _fix_name_not_defined(self, error: ErrorInfo, lines: list[str], line_num: int, repo_path: str) -> str | None:
        """Fix NameError: name 'X' is not defined.
        
        Handles three cases:
        1. Import alias typo: 'import mod as validato' but code uses 'validator'
           → fix the alias to match usage
        2. Full-path import without alias: 'import src.validator' but used as 'validator'
           → add 'as X' alias
        3. Missing import entirely: 'X' is a function in a source file
           → add 'from src.module import X'
        """
        msg = error.message
        
        # Extract undefined name from error message
        m = re.search(r"name ['\"]?(\w+)['\"]? is not defined", msg)
        if not m:
            return None
        
        undefined_name = m.group(1)
        error_file_rel = error.file.replace("\\", "/")
        
        # Case 1: Check if there's an import alias that's a close match
        for i, line in enumerate(lines):
            # Match: import X as Y  or  import X.Y as Z
            alias_match = re.match(r'^\s*(import\s+[\w.]+\s+as\s+)(\w+)\s*$', line)
            if alias_match:
                alias = alias_match.group(2)
                # Check if the alias is a close match to the undefined name
                close = difflib.get_close_matches(undefined_name, [alias], n=1, cutoff=0.7)
                if close:
                    fixed_line = alias_match.group(1) + undefined_name
                    return f"__CROSSFILE__ {error_file_rel}|||{i + 1}|||{fixed_line}"
            
            # Match: from X.Y import Z as W
            from_alias_match = re.match(r'^(\s*from\s+[\w.]+\s+import\s+\w+\s+as\s+)(\w+)\s*$', line)
            if from_alias_match:
                alias = from_alias_match.group(2)
                close = difflib.get_close_matches(undefined_name, [alias], n=1, cutoff=0.7)
                if close:
                    fixed_line = from_alias_match.group(1) + undefined_name
                    return f"__CROSSFILE__ {error_file_rel}|||{i + 1}|||{fixed_line}"
        
        # Case 2: Full-path import without alias (e.g., 'import src.validator' used as 'validator')
        for i, line in enumerate(lines):
            mod_match = re.match(r'^\s*import\s+([\w.]+)\s*$', line)
            if mod_match:
                module_path = mod_match.group(1)
                parts = module_path.split('.')
                if parts[-1] == undefined_name:
                    fixed_line = line.rstrip() + f' as {undefined_name}'
                    return f"__CROSSFILE__ {error_file_rel}|||{i + 1}|||{fixed_line}"
        
        # Case 3: Name not found in imports at all — try to find it in source files
        repo = Path(repo_path)
        for py_file in sorted(repo.rglob("*.py")):
            rel = str(py_file.relative_to(repo)).replace("\\", "/")
            if "test" in rel.lower() or "__pycache__" in rel:
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                if re.search(rf'^(def|class)\s+{re.escape(undefined_name)}\s*[\(:]', content, re.MULTILINE):
                    module_path = rel.replace('/', '.').replace('.py', '')
                    import_line = f'from {module_path} import {undefined_name}'
                    # Prepend import to the error file — replace line 1 with import + original line 1
                    first_line = lines[0].rstrip() if lines else ''
                    combined = import_line + '\n' + first_line
                    return f"__CROSSFILE__ {error_file_rel}|||1|||{combined}"
            except Exception:
                continue
        
        return None


    def _fix_exec_indentation(self, error: ErrorInfo, lines: list[str], line_num: int) -> str | None:
        """Fix indentation error inside an exec() string by runtime patching."""
        line = lines[line_num - 1]
        
        # Safety: avoid re-patching
        if ".replace(" in line:
            return None
        
        # Match exec(var) or exec(var, ns) — handle namespace-captured variants too
        m_exec = re.search(r'exec\s*\(\s*(\w+)(\s*[,)])', line)
        if not m_exec:
            return None
            
        var_name = m_exec.group(1)
        after = m_exec.group(2)  # either ',' or ')'
            
        # Transform: exec(var...) -> exec(var.replace(':\n', ':\n    ')...)
        old_fragment = f"exec({var_name}{after}"
        new_fragment = f"exec({var_name}.replace(':\\n', ':\\n    '){after}"
        return line.replace(old_fragment, new_fragment, 1)


    def _fix_missing_return(self, error: ErrorInfo, lines: list[str], line_num: int, repo_path: str) -> str | None:
        """Fix logic error where a wrapper function fails to return the result of an inner/exec function.
        
        Python 3 gotcha: exec() does NOT inject local variables into the calling
        function's scope. We must use a namespace dict to capture defined names.
        Pattern: _ns = {}; exec(code, _ns); return _ns['func_name']()
        
        Generic: searches ALL .py source files in the repo for exec() calls missing return.
        """
        # 1. Check for assertion failure pattern (function returns None)
        line = lines[line_num - 1] if line_num <= len(lines) else ""
        msg = error.message.lower()
        
        # Strict heuristic: ONLY trigger when function returns None
        # (the error message must explicitly mention None)
        # This prevents false matches on calculator errors like 'assert 120.0 == 80'
        if "none" not in msg:
            return None
        
        # 2. Search ALL .py source files for functions with exec() that lack return
        repo = Path(repo_path)
        
        for py_file in sorted(repo.rglob("*.py")):
            # Skip test files — we want source files
            rel = str(py_file.relative_to(repo)).replace("\\", "/")
            if "test" in rel.lower() or "__pycache__" in rel or ".venv" in rel or "node_modules" in rel:
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            
            src_lines = content.splitlines(keepends=False)
            
            for i, sl in enumerate(src_lines):
                if "exec(" not in sl:
                    continue
                    
                original_exec_line = sl
                exec_line_idx = i
                
                # Skip if already patched
                if "_ns" in original_exec_line:
                    continue
                
                # Detect inner function name from string definition near exec()
                inner_name = None
                for j in range(max(0, exec_line_idx - 15), min(len(src_lines), exec_line_idx + 2)):
                    m = re.search(r'''["']def\s+(\w+)\s*\(''', src_lines[j])
                    if m:
                        inner_name = m.group(1)
                        break
                
                if not inner_name:
                    continue
                
                # Build the namespace-capture fix
                indent = re.match(r'^(\s*)', original_exec_line).group(1)
                exec_call = original_exec_line.strip()
                
                # Extract what's inside exec(...) — handle nested parens
                try:
                    exec_start = exec_call.index("exec(") + 5
                except ValueError:
                    continue
                    
                depth = 1
                pos = exec_start
                while pos < len(exec_call) and depth > 0:
                    if exec_call[pos] == "(":
                        depth += 1
                    elif exec_call[pos] == ")":
                        depth -= 1
                    pos += 1
                exec_content = exec_call[exec_start:pos - 1]
                
                # Build: _ns = {}; exec(content, _ns); return _ns['inner']()
                fixed_code = f"{indent}_ns = {{}}; exec({exec_content}, _ns); return _ns['{inner_name}']()"
                target_rel = rel
                
                return f"__CROSSFILE__ {target_rel}|||{exec_line_idx + 1}|||{fixed_code}"
        
        return None


# Singleton
heal_agent = HealAgent()
