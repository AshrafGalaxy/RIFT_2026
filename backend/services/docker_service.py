"""
RIFT 2026 — Docker Sandbox Service

Runs test commands inside isolated Docker containers.
Falls back to local subprocess execution if Docker is unavailable.
"""
import subprocess
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("rift.docker_service")

# Try to import Docker SDK, but don't fail if unavailable
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from config import SANDBOX_IMAGE, SANDBOX_TIMEOUT


class DockerService:
    """Manages sandboxed test execution."""

    def __init__(self):
        self._client = None
        if DOCKER_AVAILABLE:
            try:
                self._client = docker.from_env()
                self._client.ping()
                logger.info("Docker daemon connected.")
            except Exception as e:
                logger.warning(f"Docker unavailable ({e}), using local fallback.")
                self._client = None

    @property
    def is_docker_available(self) -> bool:
        return self._client is not None

    def run_sandbox(
        self,
        repo_path: str,
        commands: list[str],
        timeout: int = SANDBOX_TIMEOUT,
    ) -> dict:
        """
        Execute commands in a sandboxed environment.

        Args:
            repo_path: Path to the cloned repo.
            commands: List of shell commands to run sequentially.
            timeout: Max seconds per command.

        Returns:
            dict with keys: stdout, stderr, exit_code
        """
        if self.is_docker_available:
            return self._run_docker(repo_path, commands, timeout)
        else:
            return self._run_local(repo_path, commands, timeout)

    def _run_docker(
        self, repo_path: str, commands: list[str], timeout: int
    ) -> dict:
        """Run inside Docker container."""
        combined_cmd = " && ".join(commands)
        try:
            container = self._client.containers.run(
                image=SANDBOX_IMAGE,
                command=f"/bin/bash -c '{combined_cmd}'",
                volumes={
                    str(Path(repo_path).resolve()): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                working_dir="/workspace",
                detach=True,
                mem_limit="512m",
                cpu_period=100000,
                cpu_quota=50000,  # 50% CPU
                network_mode="bridge",
            )
            result = container.wait(timeout=timeout)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            exit_code = result.get("StatusCode", -1)

            container.remove(force=True)

            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as e:
            logger.error(f"Docker execution failed: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
            }

    def _run_local(
        self, repo_path: str, commands: list[str], timeout: int
    ) -> dict:
        """Fallback: run locally via subprocess."""
        import platform
        import sys

        # Resolve to absolute path and validate
        resolved_path = str(Path(repo_path).resolve())
        if not Path(resolved_path).is_dir():
            return {
                "stdout": "",
                "stderr": f"Directory not found: {resolved_path}",
                "exit_code": -1,
            }

        # Use the current Python interpreter to avoid PATH conflicts
        # (e.g., MSYS2's python.exe intercepting the command on Windows)
        python_exe = sys.executable
        logger.info(f"Using Python executable: {python_exe}")

        all_stdout = []
        all_stderr = []
        last_exit_code = 0

        for cmd in commands:
            # Replace generic 'python' with the actual interpreter path
            if cmd.startswith("python -m ") or cmd.startswith("python "):
                cmd = cmd.replace("python ", f'"{python_exe}" ', 1)
            elif cmd.startswith("pip "):
                # Use python -m pip to ensure correct pip
                cmd = f'"{python_exe}" -m ' + cmd

            # Windows compatibility: convert bash-style redirects
            if platform.system() == "Windows":
                cmd = cmd.replace("2>&1", "")  # Windows handles stderr separately
                cmd = cmd.replace("2>/dev/null", "")

            try:
                logger.info(f"Running: {cmd} (in {resolved_path})")
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=resolved_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                all_stdout.append(result.stdout)
                all_stderr.append(result.stderr)
                last_exit_code = result.returncode

                # If install step fails, still try to run tests
                if result.returncode != 0 and "install" in cmd.lower():
                    logger.warning(f"Install command failed (rc={result.returncode}), continuing...")
                    continue

            except subprocess.TimeoutExpired:
                all_stderr.append(f"Command timed out after {timeout}s: {cmd}")
                last_exit_code = -1
                break
            except Exception as e:
                all_stderr.append(f"Command error: {e}")
                last_exit_code = -1
                break

        return {
            "stdout": "\n".join(all_stdout),
            "stderr": "\n".join(all_stderr),
            "exit_code": last_exit_code,
        }


# Singleton
docker_service = DockerService()
