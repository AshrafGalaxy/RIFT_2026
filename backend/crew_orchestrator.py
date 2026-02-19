"""
RIFT 2026 — CrewAI Crew Orchestrator

Defines 5 CrewAI Agents, each with a specific role and tool,
orchestrated as a sequential Crew pipeline.

This replaces the plain-Python orchestrator with a proper
multi-agent framework (CrewAI) as required by the hackathon.
"""
import json
import logging
import os
import time

from dotenv import load_dotenv

# Load .env before any CrewAI imports
load_dotenv()

from crewai import Agent, Crew, Task, Process

from config import MAX_ITERATIONS
from models import (
    Fix,
    FixStatus,
    Iteration,
    RunRequest,
    RunResult,
    RunStatus,
    TestOutput,
    ErrorInfo,
)
from crewai_tools import CloneTool, DiscoverTool, AnalyzeTool, HealTool, VerifyTool
from services.results_service import results_service
from utils import compute_score, format_branch_name, now_iso

logger = logging.getLogger("rift.crew_orchestrator")


def _get_llm_config() -> str:
    """
    Get the LLM model string for CrewAI.
    Uses Gemini (Google) as the primary LLM.
    Falls back to Claude only if Gemini key is missing and Claude key exists.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if gemini_key:
        # Use Gemini — set the key and REMOVE Anthropic key from env
        # to prevent litellm from accidentally routing to Claude
        os.environ["GEMINI_API_KEY"] = gemini_key
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        model = os.getenv("CREWAI_LLM_MODEL", "gemini/gemini-2.0-flash")
        logger.info(f"Using LLM: {model} (Gemini)")
        return model
    elif anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
        model = "anthropic/claude-sonnet-4-20250514"
        logger.info(f"Using LLM: {model} (Claude)")
        return model
    else:
        logger.warning("No API keys found! Set GEMINI_API_KEY in .env")
        return "gemini/gemini-2.0-flash"


# ===================== DEFINE AGENTS =====================

def create_agents(llm_model: str) -> dict:
    """Create all 5 CrewAI agents."""

    clone_agent = Agent(
        role="Repository Clone Specialist",
        goal="Clone the target GitHub repository to a local workspace",
        backstory=(
            "You are a DevOps specialist responsible for securely cloning "
            "repositories from GitHub. You ensure the repo is available "
            "locally for the pipeline to work on."
        ),
        tools=[CloneTool()],
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )

    discover_agent = Agent(
        role="Test Discovery & Execution Specialist",
        goal="Scan the repository, detect the project type and test framework, install dependencies, and run all tests",
        backstory=(
            "You are a CI/CD expert who can identify any project type "
            "(Python, Node.js) and its test framework (pytest, jest, mocha, etc.). "
            "You run tests in a sandboxed environment and report results."
        ),
        tools=[DiscoverTool()],
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )

    analyze_agent = Agent(
        role="Error Analysis Specialist",
        goal="Parse test output and classify every error into: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, or INDENTATION",
        backstory=(
            "You are a code analysis expert who can read test output "
            "(stdout/stderr) and precisely identify the type, file, and "
            "line number of each error. Your classifications are accurate "
            "and follow the exact 6 categories required."
        ),
        tools=[AnalyzeTool()],
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )

    heal_agent = Agent(
        role="Code Healing Specialist",
        goal="Generate targeted fixes for each classified error, create a fix branch, and commit changes with [AI-AGENT] prefix",
        backstory=(
            "You are an autonomous code repair agent. For each error, you "
            "generate a targeted fix: adding missing imports, fixing indentation, "
            "correcting syntax, etc. You create a branch named "
            "TEAM_NAME_LEADER_NAME_AI_Fix and commit each fix with the "
            "[AI-AGENT] prefix. You NEVER push to main or master."
        ),
        tools=[HealTool()],
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )

    verify_agent = Agent(
        role="Verification Specialist",
        goal="Re-run the test suite on the fixed branch to verify all fixes resolved the errors",
        backstory=(
            "You are the final quality gate. After fixes are applied, you "
            "re-run the entire test suite to confirm everything passes. "
            "If tests still fail, you report the remaining failures."
        ),
        tools=[VerifyTool()],
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )

    return {
        "clone": clone_agent,
        "discover": discover_agent,
        "analyze": analyze_agent,
        "heal": heal_agent,
        "verify": verify_agent,
    }


# ===================== PIPELINE =====================

async def run_pipeline(request: RunRequest) -> RunResult:
    """
    Execute the self-healing pipeline using CrewAI multi-agent framework.

    This function orchestrates the healing loop:
    1. Clone Agent clones the repo
    2. Discover Agent runs tests
    3. Loop up to MAX_ITERATIONS:
       a. Analyze Agent classifies errors
       b. Heal Agent applies fixes
       c. Verify Agent re-runs tests
    4. Compute score and save results.json
    """
    start_time = time.time()
    started_at = now_iso()
    branch_name = format_branch_name(request.team_name, request.leader_name)
    all_fixes: list[Fix] = []
    iterations: list[Iteration] = []
    total_commits = 0

    result = RunResult(
        repo_url=request.repo_url,
        branch_name=branch_name,
        team_name=request.team_name,
        leader_name=request.leader_name,
        status=RunStatus.RUNNING,
        started_at=started_at,
    )

    try:
        llm_model = _get_llm_config()
        agents = create_agents(llm_model)

        # ========== STEP 1: CLONE via CrewAI ==========
        logger.info("=" * 60)
        logger.info("CREWAI STEP 1: CLONE")
        logger.info("=" * 60)

        clone_task = Task(
            description=(
                f"Clone the GitHub repository at '{request.repo_url}' "
                f"for team '{request.team_name}'. "
                f"Use the clone_repository tool with repo_url='{request.repo_url}' "
                f"and team_name='{request.team_name}'. "
                f"Return the repo_path from the tool result."
            ),
            expected_output="JSON with status and repo_path",
            agent=agents["clone"],
        )

        clone_crew = Crew(
            agents=[agents["clone"]],
            tasks=[clone_task],
            process=Process.sequential,
            verbose=True,
        )

        clone_result = clone_crew.kickoff()
        clone_output = _parse_json_safe(str(clone_result))
        repo_path = clone_output.get("repo_path", "")

        if not repo_path or not os.path.exists(repo_path):
            logger.warning(f"CrewAI returned invalid path: '{repo_path}'. Using fallback.")
            # Fallback: use our agent directly
            from agents.clone_agent import clone_agent
            repo_path = clone_agent.run(request.repo_url, request.team_name)

        logger.info(f"Repo cloned to: {repo_path}")

        # ========== STEP 2: DISCOVER via CrewAI ==========
        logger.info("=" * 60)
        logger.info("CREWAI STEP 2: DISCOVER & RUN TESTS")
        logger.info("=" * 60)

        discover_task = Task(
            description=(
                f"Discover and run all tests in the repository at '{repo_path}'. "
                f"Use the discover_and_run_tests tool with repo_path='{repo_path}'. "
                f"Return the full JSON result with stdout, stderr, exit_code, "
                f"passed, failed, total, and framework fields."
            ),
            expected_output="JSON with test results including passed, failed, total counts",
            agent=agents["discover"],
        )

        discover_crew = Crew(
            agents=[agents["discover"]],
            tasks=[discover_task],
            process=Process.sequential,
            verbose=True,
        )

        discover_result = discover_crew.kickoff()
        test_data = _parse_json_safe(str(discover_result))

        # Fallback if CrewAI didn't return structured data
        if "passed" not in test_data:
            from agents.discover_agent import discover_agent
            test_output = discover_agent.run(repo_path)
            test_data = test_output.model_dump()

        test_output = TestOutput(**{k: test_data.get(k, v) for k, v in TestOutput().model_dump().items() if k in test_data} if test_data else {})
        # Re-create properly
        test_output = TestOutput(
            stdout=test_data.get("stdout", ""),
            stderr=test_data.get("stderr", ""),
            exit_code=test_data.get("exit_code", -1),
            passed=test_data.get("passed", 0),
            failed=test_data.get("failed", 0),
            total=test_data.get("total", 0),
            framework=test_data.get("framework", "unknown"),
        )

        initial_iteration = Iteration(
            number=0,
            passed=test_output.passed,
            failed=test_output.failed,
            total=test_output.total,
            status=RunStatus.PASSED if test_output.failed == 0 else RunStatus.FAILED,
            stdout=test_output.stdout[:2000],
            stderr=test_output.stderr[:2000],
            timestamp=now_iso(),
        )
        iterations.append(initial_iteration)

        # Already passing?
        if test_output.failed == 0 and test_output.exit_code == 0:
            logger.info("All tests PASS — no healing needed!")
            elapsed = time.time() - start_time
            result.status = RunStatus.PASSED
            result.iterations = iterations
            result.score = compute_score(0, elapsed, True)
            result.finished_at = now_iso()
            results_service.save(result)
            return result

        # ========== HEALING LOOP via CrewAI ==========
        current_stdout = test_output.stdout
        current_stderr = test_output.stderr
        current_framework = test_output.framework
        current_exit_code = test_output.exit_code
        current_passed = test_output.passed
        current_failed = test_output.failed
        current_total = test_output.total

        for i in range(1, MAX_ITERATIONS + 1):
            logger.info("=" * 60)
            logger.info(f"CREWAI HEALING ITERATION {i}/{MAX_ITERATIONS}")
            logger.info("=" * 60)

            # --- ANALYZE via CrewAI ---
            analyze_task = Task(
                description=(
                    f"Analyze the test output and classify all errors. "
                    f"Use the analyze_errors tool with:\n"
                    f"  stdout: (the test stdout output)\n"
                    f"  stderr: (the test stderr output)\n"
                    f"  framework: '{current_framework}'\n"
                    f"  repo_path: '{repo_path}'\n"
                    f"The stdout is: {current_stdout[:3000]}\n"
                    f"The stderr is: {current_stderr[:3000]}\n"
                    f"Return the JSON list of classified errors."
                ),
                expected_output="JSON list of errors with file, line_number, bug_type, message",
                agent=agents["analyze"],
            )

            analyze_crew = Crew(
                agents=[agents["analyze"]],
                tasks=[analyze_task],
                process=Process.sequential,
                verbose=True,
            )

            analyze_result = analyze_crew.kickoff()
            errors_data = _parse_json_safe(str(analyze_result))

            # Parse errors
            errors_list = []
            if isinstance(errors_data, list):
                errors_list = errors_data
            elif isinstance(errors_data, dict) and "status" != "error":
                errors_list = [errors_data]

            if not errors_list:
                # Fallback to direct agent
                from agents.analyze_agent import analyze_agent
                error_objs = analyze_agent.run(
                    current_stdout, current_stderr, current_framework, repo_path
                )
                errors_list = [e.model_dump() for e in error_objs]

            if not errors_list:
                logger.info(f"[Iteration {i}] No errors detected.")
                iter_result = Iteration(
                    number=i, passed=current_passed, failed=current_failed,
                    total=current_total, errors_found=0, fixes_applied=0,
                    status=RunStatus.FAILED,
                    stdout=current_stdout[:2000], stderr=current_stderr[:2000],
                    timestamp=now_iso(),
                )
                iterations.append(iter_result)
                break

            # --- HEAL via CrewAI ---
            errors_json = json.dumps(errors_list)
            heal_task = Task(
                description=(
                    f"Apply fixes for {len(errors_list)} classified errors. "
                    f"Use the heal_code tool with:\n"
                    f"  repo_path: '{repo_path}'\n"
                    f"  errors_json: '{errors_json}'\n"
                    f"  team_name: '{request.team_name}'\n"
                    f"  leader_name: '{request.leader_name}'\n"
                    f"  iteration: {i}\n"
                    f"Return the full JSON result with fixes, branch_name, commit_count."
                ),
                expected_output="JSON with fixes array, branch_name, and commit_count",
                agent=agents["heal"],
            )

            heal_crew = Crew(
                agents=[agents["heal"]],
                tasks=[heal_task],
                process=Process.sequential,
                verbose=True,
            )

            heal_result = heal_crew.kickoff()
            heal_data = _parse_json_safe(str(heal_result))

            new_commits = heal_data.get("commit_count", 0)
            fixes_data = heal_data.get("fixes", [])

            if not fixes_data and not new_commits:
                # Fallback
                from agents.heal_agent import heal_agent
                error_objs = [ErrorInfo(**_sanitize_error(e)) for e in errors_list]
                fix_objs, branch_name, new_commits = heal_agent.run(
                    repo_path, error_objs, request.team_name,
                    request.leader_name, i
                )
                fixes_data = [f.model_dump() for f in fix_objs]

            for fd in fixes_data:
                all_fixes.append(Fix(**{k: fd[k] for k in Fix.model_fields if k in fd}))
            total_commits += new_commits

            # --- VERIFY via CrewAI ---
            verify_task = Task(
                description=(
                    f"Re-run all tests on the fixed branch to verify the fixes. "
                    f"Use the verify_fixes tool with repo_path='{repo_path}'. "
                    f"Return the full JSON result with pass/fail counts."
                ),
                expected_output="JSON with passed, failed, total, exit_code",
                agent=agents["verify"],
            )

            verify_crew = Crew(
                agents=[agents["verify"]],
                tasks=[verify_task],
                process=Process.sequential,
                verbose=True,
            )

            verify_result = verify_crew.kickoff()
            verify_data = _parse_json_safe(str(verify_result))

            if "passed" not in verify_data:
                from agents.verify_agent import verify_agent
                v_output = verify_agent.run(repo_path)
                verify_data = v_output.model_dump()

            current_stdout = verify_data.get("stdout", "")
            current_stderr = verify_data.get("stderr", "")
            current_exit_code = verify_data.get("exit_code", -1)
            current_passed = verify_data.get("passed", 0)
            current_failed = verify_data.get("failed", 0)
            current_total = verify_data.get("total", 0)

            applied_count = sum(
                1 for f in fixes_data
                if isinstance(f, dict) and f.get("status") == "APPLIED"
            )

            iter_result = Iteration(
                number=i,
                passed=current_passed,
                failed=current_failed,
                total=current_total,
                errors_found=len(errors_list),
                fixes_applied=applied_count,
                status=RunStatus.PASSED if current_failed == 0 else RunStatus.FAILED,
                stdout=current_stdout[:2000],
                stderr=current_stderr[:2000],
                timestamp=now_iso(),
            )
            iterations.append(iter_result)

            if current_failed == 0 and current_exit_code == 0:
                logger.info(f"All tests PASSED on iteration {i}!")
                for fix in all_fixes:
                    if fix.status == FixStatus.APPLIED:
                        fix.status = FixStatus.VERIFIED
                break
            else:
                logger.info(
                    f"[Iteration {i}] Still {current_failed} failures."
                )

        # ========== FINALIZE ==========
        elapsed = time.time() - start_time
        all_passed = current_failed == 0 and current_exit_code == 0

        result.fixes = all_fixes
        result.iterations = iterations
        result.total_commits = total_commits
        result.status = RunStatus.PASSED if all_passed else RunStatus.FAILED
        result.score = compute_score(total_commits, elapsed, all_passed)
        result.finished_at = now_iso()

        logger.info("=" * 60)
        logger.info(f"CREWAI PIPELINE COMPLETE: {result.status.value}")
        logger.info(f"Score: {result.score} | Commits: {total_commits}")
        logger.info(f"Time: {elapsed:.1f}s | Iterations: {len(iterations)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        result.status = RunStatus.ERROR
        result.error_message = str(e)
        result.finished_at = now_iso()
        result.iterations = iterations
        result.fixes = all_fixes
        result.score = 0

    results_service.save(result)
    return result


def _sanitize_error(raw: dict) -> dict:
    """Clean up an error dict from AI output before passing to ErrorInfo."""
    if not isinstance(raw, dict):
        return {"file": "unknown", "line_number": 0, "bug_type": "SYNTAX", "message": str(raw)}
    return {
        "file": raw.get("file") or "unknown",
        "line_number": int(raw.get("line_number") or 0),
        "bug_type": raw.get("bug_type") or "SYNTAX",
        "message": raw.get("message") or "",
        "code_snippet": raw.get("code_snippet") or "",
    }


def _parse_json_safe(text: str) -> dict | list:
    """Try to extract and parse JSON from CrewAI agent output text."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON in the text
    import re
    # Look for JSON object
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Look for JSON array
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}
