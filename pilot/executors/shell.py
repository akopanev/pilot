"""Shell command executor."""

from __future__ import annotations

import subprocess

from pilot.executors.result import ExecutorResult


class ShellExecutor:
    """Runs shell commands via subprocess."""

    def run(self, command: str, **kwargs) -> ExecutorResult:
        proc = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
        )
        return ExecutorResult(
            output=proc.stdout,
            exit_code=proc.returncode,
            error=proc.stderr if proc.returncode != 0 else None,
        )
