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
            known_signals: set[str] | None = None) -> ExecutorResult:
        proc = subprocess.run(
            prompt,
            shell=True,
            capture_output=True,
            text=True,
        )

        output = proc.stdout
        signals = parse_signals(output, known_signals)

        return ExecutorResult(
            output=output,
            exit_code=proc.returncode,
            error=proc.stderr.strip() if proc.returncode != 0 else None,
            signals=signals,
        )
