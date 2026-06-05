"""OpenCode executor — AI coding CLI (opencode.ai)."""

from __future__ import annotations

import subprocess

from pilot.signals import SignalScanner
from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog


class OpenCodeExecutor:
    """Runs opencode CLI.

    Command: opencode run [-m MODEL] PROMPT
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None,
            args: list[str] | None = None) -> ExecutorResult:
        cmd = ["opencode", "run"]
        if model:
            cmd.extend(["-m", model])
        # Raw per-runner args before the positional prompt.
        if args:
            cmd += args
        cmd.append(prompt)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        start_cancel_watchdog(cancel, proc)

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
                kill_process_group(proc)
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
