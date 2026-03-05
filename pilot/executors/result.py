"""Shared types and helpers for all executors."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from dataclasses import dataclass, field

from pilot.signals import Signal


@dataclass
class ExecutorResult:
    output: str
    exit_code: int
    error: str | None
    signals: list[Signal] = field(default_factory=list)


def kill_process_group(proc: subprocess.Popen) -> None:
    """Graceful shutdown: SIGTERM -> wait -> SIGKILL."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def start_cancel_watchdog(cancel: threading.Event | None,
                          proc: subprocess.Popen) -> None:
    """Spawn a daemon thread that kills proc when cancel is set.

    PEP 475 auto-retries interrupted reads, so checking cancel inside
    a `for line in proc.stdout` loop doesn't work — we must kill the
    process from another thread to unblock the pipe read.
    """
    if not cancel:
        return

    def _watchdog():
        cancel.wait()
        if proc.poll() is None:
            kill_process_group(proc)

    threading.Thread(target=_watchdog, daemon=True).start()
