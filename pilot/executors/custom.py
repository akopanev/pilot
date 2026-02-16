"""Custom script executor — writes prompt to temp file, passes path as argument.

Matches Ralphex's CustomExecutor: script receives prompt file path as single argument,
output is streamed line-by-line with signal detection.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult, check_error_patterns


class CustomExecutor:
    """Runs a custom script with prompt content as a temp file argument."""

    def __init__(self, script: str, error_patterns: list[str] | None = None):
        self.script = script
        self.error_patterns = error_patterns or []

    def run(self, prompt: str, model: str | None = None,
            args: list[str] | None = None) -> ExecutorResult:
        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="pilot-prompt-", delete=False,
        ) as f:
            f.write(prompt)
            prompt_path = f.name

        try:
            return self._execute(prompt_path, args)
        finally:
            os.unlink(prompt_path)

    def _execute(self, prompt_path: str,
                 args: list[str] | None = None) -> ExecutorResult:
        cmd = [self.script]
        if args:
            cmd.extend(args)
        cmd.append(prompt_path)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout
            text=True,
            start_new_session=True,
        )

        output_lines: list[str] = []
        all_signals: list[Signal] = []

        try:
            for line in proc.stdout:
                print(line, end="", flush=True)
                output_lines.append(line)

                for sig in parse_signals(line):
                    all_signals.append(sig)

            proc.wait()
        except KeyboardInterrupt:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            raise

        full_output = "".join(output_lines)

        if matched := check_error_patterns(full_output, self.error_patterns):
            return ExecutorResult(
                output=full_output,
                exit_code=proc.returncode,
                error=f"detected error pattern: {matched}",
                signals=all_signals,
            )

        return ExecutorResult(
            output=full_output,
            exit_code=proc.returncode,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            signals=all_signals,
        )
