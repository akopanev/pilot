"""Generic agent executor — for tools that output plain text (opencode, aider, etc.).

Streams stdout line-by-line without JSON parsing. Each tool is invoked by its
binary name with standard -p and --model arguments.
"""

from __future__ import annotations

import os
import signal
import subprocess

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult, check_error_patterns, write_file


class GenericExecutor:
    """Runs any CLI tool as a subprocess with plain-text streaming.

    Command pattern: <tool> [--model MODEL] -p PROMPT
    Output is streamed line-by-line with signal detection.
    """

    def __init__(self, tool: str, error_patterns: list[str] | None = None):
        self.tool = tool
        self.error_patterns = error_patterns or []

    def _build_command(self, prompt: str, model: str | None,
                       args: list[str] | None = None) -> list[str]:
        cmd = [self.tool]
        if model:
            cmd.extend(["--model", model])
        if args:
            cmd.extend(args)
        cmd.extend(["-p", prompt])
        return cmd

    def run(self, prompt: str, model: str | None = None,
            args: list[str] | None = None) -> ExecutorResult:
        cmd = self._build_command(prompt, model, args)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
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
                    if sig.type == "update":
                        write_file(sig.path, sig.payload)

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
