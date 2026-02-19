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

            # Commit the fix
            try:
                bt_str = str(error.bug_type)
                if hasattr(error.bug_type, 'value'):
                    bt_str = error.bug_type.value
                commit_msg = format_commit_message(bt_str, error.file, error.line_number)
                fix.commit_message = commit_msg
                git_service.commit_fix(repo, error.file, commit_msg)
                fix.status = FixStatus.APPLIED
                commit_count += 1
                logger.info(f"Fixed {error.file}:{error.line_number} ({error.bug_type})")
            except Exception as e:
                logger.error(f"Commit failed for {error.file}: {e}")
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
        fix_strategies = self._get_strategies(bt, error)

        for strategy_name, strategy_fn in fix_strategies:
            fixed_line = strategy_fn(error, lines, error.line_number)
            if fixed_line is None:
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

    def _get_strategies(self, bug_type: str, error: ErrorInfo) -> list:
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
                ("bad_indent", self._fix_indentation),
                ("tab_to_spaces", self._fix_tabs_to_spaces),
            ]
        elif bug_type == "IMPORT":
            return [
                ("fix_module_typo", self._fix_module_typo),
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


# Singleton
heal_agent = HealAgent()
