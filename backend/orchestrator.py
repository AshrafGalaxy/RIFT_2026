"""
RIFT 2026 — Orchestrator

Master pipeline that coordinates all 5 agents:
Clone → Discover → (loop ≤5×: Analyze → Heal → Verify) → Score → Save results.json
"""
import logging
import time
from datetime import datetime

from config import MAX_ITERATIONS
from models import (
    Fix,
    FixStatus,
    Iteration,
    RunRequest,
    RunResult,
    RunStatus,
    TestOutput,
)
from agents.clone_agent import clone_agent
from agents.discover_agent import discover_agent
from agents.analyze_agent import analyze_agent
from agents.heal_agent import heal_agent
from agents.verify_agent import verify_agent
from services.results_service import results_service
from utils import compute_score, format_branch_name, now_iso

logger = logging.getLogger("rift.orchestrator")


async def run_pipeline(request: RunRequest) -> RunResult:
    """
    Execute the full self-healing CI/CD pipeline.

    Steps:
        1. CLONE the repository
        2. DISCOVER + run tests
        3. If all pass → return PASSED immediately
        4. Loop up to MAX_ITERATIONS:
           a. ANALYZE errors
           b. HEAL (fix + commit + push)
           c. VERIFY (re-run tests)
           d. If all pass → break
        5. Compute score
        6. Write results.json
        7. Return RunResult

    Returns:
        RunResult containing all fixes, iterations, score, and status.
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
        # ========== STEP 1: CLONE ==========
        logger.info("=" * 60)
        logger.info("STEP 1: CLONE")
        logger.info("=" * 60)

        repo_path = clone_agent.run(request.repo_url, request.team_name)

        # ========== STEP 2: DISCOVER + RUN TESTS ==========
        logger.info("=" * 60)
        logger.info("STEP 2: DISCOVER & RUN TESTS")
        logger.info("=" * 60)

        test_output = discover_agent.run(repo_path)
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

        # ========== CHECK: Already passing? ==========
        if test_output.failed == 0 and test_output.exit_code == 0:
            logger.info("✅ All tests already PASS — no healing needed!")
            elapsed = time.time() - start_time
            result.status = RunStatus.PASSED
            result.iterations = iterations
            result.score = compute_score(0, elapsed, True)
            result.finished_at = now_iso()
            results_service.save(result)
            return result

        # ========== STEP 3-5: HEALING LOOP ==========
        current_output = test_output

        for i in range(1, MAX_ITERATIONS + 1):
            logger.info("=" * 60)
            logger.info(f"HEALING ITERATION {i}/{MAX_ITERATIONS}")
            logger.info("=" * 60)

            # --- ANALYZE ---
            logger.info(f"[Iteration {i}] ANALYZE: parsing errors...")
            errors = analyze_agent.run(
                current_output.stdout,
                current_output.stderr,
                current_output.framework,
                repo_path,
            )

            if not errors:
                logger.info(f"[Iteration {i}] No errors detected by analyzer.")
                # Tests still failing but analyzer can't parse errors
                iter_result = Iteration(
                    number=i,
                    passed=current_output.passed,
                    failed=current_output.failed,
                    total=current_output.total,
                    errors_found=0,
                    fixes_applied=0,
                    status=RunStatus.FAILED,
                    stdout=current_output.stdout[:2000],
                    stderr=current_output.stderr[:2000],
                    timestamp=now_iso(),
                )
                iterations.append(iter_result)
                break

            # --- HEAL ---
            logger.info(f"[Iteration {i}] HEAL: applying {len(errors)} fixes...")
            fixes, branch_name, new_commits = heal_agent.run(
                repo_path, errors, request.team_name, request.leader_name, i
            )
            all_fixes.extend(fixes)
            total_commits += new_commits

            # --- VERIFY ---
            logger.info(f"[Iteration {i}] VERIFY: re-running tests...")
            current_output = verify_agent.run(repo_path)

            applied_count = sum(1 for f in fixes if f.status == FixStatus.APPLIED)
            iter_result = Iteration(
                number=i,
                passed=current_output.passed,
                failed=current_output.failed,
                total=current_output.total,
                errors_found=len(errors),
                fixes_applied=applied_count,
                status=RunStatus.PASSED if current_output.failed == 0 else RunStatus.FAILED,
                stdout=current_output.stdout[:2000],
                stderr=current_output.stderr[:2000],
                timestamp=now_iso(),
            )
            iterations.append(iter_result)

            # --- Check if all pass ---
            if current_output.failed == 0 and current_output.exit_code == 0:
                logger.info(f"✅ All tests PASSED on iteration {i}!")
                # Mark fixes as verified
                for fix in all_fixes:
                    if fix.status == FixStatus.APPLIED:
                        fix.status = FixStatus.VERIFIED
                break
            else:
                logger.info(
                    f"[Iteration {i}] Still {current_output.failed} failures. "
                    f"Continuing..."
                )

        # ========== FINALIZE ==========
        elapsed = time.time() - start_time
        all_passed = (
            current_output.failed == 0 and current_output.exit_code == 0
        )

        result.fixes = all_fixes
        result.iterations = iterations
        result.total_commits = total_commits
        result.status = RunStatus.PASSED if all_passed else RunStatus.FAILED
        result.score = compute_score(total_commits, elapsed, all_passed)
        result.finished_at = now_iso()

        logger.info("=" * 60)
        logger.info(f"PIPELINE COMPLETE: {result.status.value}")
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

    # Always save results
    results_service.save(result)
    return result
