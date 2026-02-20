"""
RIFT 2026 — SSE Event Manager

Provides a global event queue for streaming pipeline progress
to the frontend via Server-Sent Events (SSE).

Uses asyncio.Queue with thread-safe put from sync agent code.
"""
import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger("rift.sse_manager")


class SSEManager:
    """Manages a per-run asyncio queue for SSE events."""

    def __init__(self):
        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def create_queue(self, loop: asyncio.AbstractEventLoop) -> asyncio.Queue:
        """Create a fresh event queue for a new run."""
        self._queue = asyncio.Queue()
        self._loop = loop
        return self._queue

    @property
    def queue(self) -> Optional[asyncio.Queue]:
        return self._queue

    def emit(self, event_type: str, data: dict | str):
        """Push an event into the queue (thread-safe)."""
        if self._queue is None or self._loop is None:
            return
        payload = data if isinstance(data, str) else json.dumps(data)
        event = {"event": event_type, "data": payload}
        # Thread-safe: schedule put_nowait on the event loop from any thread
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    # Convenience methods
    def step(self, step_name: str, step_index: int, message: str = ""):
        self.emit("step", {
            "step": step_name,
            "index": step_index,
            "message": message or f"Starting {step_name}...",
        })

    def agent(self, agent_name: str, message: str, msg_type: str = "info"):
        self.emit("agent", {
            "agent": agent_name,
            "message": message,
            "type": msg_type,
        })

    def iteration(self, number: int, passed: int, failed: int, total: int, status: str, fixes_applied: int = 0, new_fixes: list = None):
        self.emit("iteration", {
            "number": number,
            "passed": passed,
            "failed": failed,
            "total": total,
            "status": status,
            "fixes_applied": fixes_applied,
            "new_fixes": new_fixes or [],
        })

    def log(self, message: str, msg_type: str = "info"):
        self.emit("log", {"message": message, "type": msg_type})

    def error(self, message: str):
        self.emit("error", {"message": message})

    def result(self, data: dict):
        self.emit("result", data)

    def done(self):
        self.emit("done", {"message": "Pipeline complete"})
