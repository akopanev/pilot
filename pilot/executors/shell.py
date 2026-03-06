"""Shell executor — runs commands/scripts, streams stdout in real-time."""

from __future__ import annotations

import subprocess

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult


class ShellExecutor:
    """Runs shell commands. The 'prompt' is the command to execute.

    Signals are parsed from stdout in real-time as lines arrive.
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None) -> ExecutorResult:
        proc = subprocess.Popen(
            ["bash", "-c", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        lines: list[str] = []
        all_signals = []

        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)

            # Parse signals from this line
            sigs = parse_signals(line, known_signals)
            if sigs:
                all_signals.extend(sigs)
                if on_signal:
                    for sig in sigs:
                        on_signal(sig)
            elif line.strip() and on_output:
                on_output(line)

        proc.wait()
        stderr = proc.stderr.read() if proc.stderr else ""

        output = "\n".join(lines)
        return ExecutorResult(
            output=output,
            exit_code=proc.returncode,
            error=stderr.strip() if proc.returncode != 0 else None,
            signals=all_signals,
        )
