"""OpenCode executor — AI coding CLI (opencode.ai)."""

from __future__ import annotations

import os
import signal
import subprocess

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult


class OpenCodeExecutor:
    """Runs opencode CLI in non-interactive dangerous mode.

    Command: opencode run --dangerously-skip-permissions [--model MODEL] PROMPT
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None) -> ExecutorResult:
        cmd = ["opencode", "run", "--dangerously-skip-permissions"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        output_parts: list[str] = []
        all_signals: list[Signal] = []

        try:
            for line in proc.stdout:
                output_parts.append(line)
                for sig in parse_signals(line, known_signals):
                    all_signals.append(sig)

            proc.wait()
        except KeyboardInterrupt:
            _kill_process_group(proc)
            raise

        full_output = "".join(output_parts)

        return ExecutorResult(
            output=full_output,
            exit_code=proc.returncode,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            signals=all_signals,
        )


def _kill_process_group(proc: subprocess.Popen) -> None:
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
