"""Codex executor — separate stderr (progress) / stdout (response)."""

from __future__ import annotations

import os
import signal
import subprocess
import threading

from pilot.signals import Signal, parse_signals
from pilot.executors.result import ExecutorResult


class CodexExecutor:
    """Runs codex CLI with split stderr/stdout handling.

    stderr: progress display (filtered).
    stdout: the actual response.
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None) -> ExecutorResult:
        effective_model = model or "o3"
        sandbox = "full-auto"
        if os.environ.get("PILOT_DOCKER") == "1":
            sandbox = "danger-full-access"

        cmd = [
            "codex", "exec",
            "--sandbox", sandbox,
            "--skip-git-repo-check",
            "-c", f'model="{effective_model}"',
            "-c", "model_reasoning_effort=xhigh",
            "-c", "stream_idle_timeout_ms=3600000",
        ]
        cmd.append(prompt)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        stderr_result: dict = {"last_lines": [], "error": None}
        stderr_thread = threading.Thread(
            target=self._process_stderr,
            args=(proc.stderr, stderr_result),
            daemon=True,
        )
        stderr_thread.start()

        stdout_content = ""
        stdout_error = None
        try:
            stdout_content = proc.stdout.read()
        except Exception as e:
            stdout_error = str(e)

        stderr_thread.join()
        proc.wait()

        error = None
        if stderr_result["error"]:
            error = stderr_result["error"]
        elif stdout_error:
            error = stdout_error
        elif proc.returncode != 0:
            tail = "\n".join(stderr_result["last_lines"])
            error = f"codex exited with code {proc.returncode}"
            if tail:
                error += f"\nstderr: {tail}"

        all_signals = parse_signals(stdout_content, known_signals)

        return ExecutorResult(
            output=stdout_content,
            exit_code=proc.returncode,
            error=error,
            signals=all_signals,
        )

    @staticmethod
    def _process_stderr(stream, result: dict) -> None:
        """Read stderr for progress display. Captures last 5 lines for error context."""
        max_tail = 5
        tail: list[str] = []

        try:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                stored = stripped[:256] + "..." if len(stripped) > 256 else stripped
                tail.append(stored)
                if len(tail) > max_tail:
                    tail.pop(0)
        except Exception as e:
            result["error"] = str(e)

        result["last_lines"] = tail
