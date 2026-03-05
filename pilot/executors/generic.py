"""Generic CLI executor — plain text streaming for any tool."""

from __future__ import annotations

import os
import signal
import subprocess

from pilot.signals import SignalScanner
from pilot.executors.result import ExecutorResult


class GenericExecutor:
    """Runs any CLI tool as a subprocess with plain-text streaming.

    Command pattern: <tool> [--model MODEL] -p PROMPT
    """

    def __init__(self, tool: str):
        self.tool = tool

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None) -> ExecutorResult:
        cmd = [self.tool]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["-p", prompt])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        output_parts: list[str] = []
        all_signals = []
        scanner = SignalScanner(known_signals)

        try:
            for line in proc.stdout:
                output_parts.append(line)
                if on_output:
                    on_output(line)
                for sig in scanner.feed(line):
                    all_signals.append(sig)
                    if on_signal:
                        on_signal(sig)
        finally:
            if proc.poll() is None:
                _kill_process_group(proc)
            proc.wait()

        # Flush remaining buffered signals
        for sig in scanner.flush():
            all_signals.append(sig)
            if on_signal:
                on_signal(sig)

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
