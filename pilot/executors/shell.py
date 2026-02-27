"""Shell executor — runs commands/scripts, parses signals from stdout."""

from __future__ import annotations

import subprocess

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult


class ShellExecutor:
    """Runs shell commands. The 'prompt' is the command to execute.

    Signals are parsed from stdout (e.g. echo "<signal:ready>task-id").
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None) -> ExecutorResult:
        proc = subprocess.run(
            ["bash", "-c", prompt],
            capture_output=True,
            text=True,
        )

        output = proc.stdout
        signals = parse_signals(output, known_signals)
        if on_signal:
            for sig in signals:
                on_signal(sig)
        # Log non-signal lines only (signals already displayed via on_signal)
        if on_output and output:
            for line in output.splitlines():
                if line.strip() and "<signal:" not in line:
                    on_output(line)

        return ExecutorResult(
            output=output,
            exit_code=proc.returncode,
            error=proc.stderr.strip() if proc.returncode != 0 else None,
            signals=signals,
        )
