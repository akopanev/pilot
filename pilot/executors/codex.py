"""Codex executor — separate stderr (progress) / stdout (response) handling.

Matches Ralphex's CodexExecutor: stderr is streamed for filtered progress display,
stdout is captured entirely as the final response.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult, check_error_patterns


def strip_bold(text: str) -> str:
    """Remove markdown bold markers (**text**) from text."""
    result = text
    while True:
        start = result.find("**")
        if start == -1:
            break
        end = result.find("**", start + 2)
        if end == -1:
            break
        result = result[:start] + result[start + 2:end] + result[end + 2:]
    return result


class CodexExecutor:
    """Runs codex CLI with split stderr/stdout handling.

    stderr: progress display — filtered to show header block + bold summaries.
    stdout: the actual response — captured entirely as Result.output.
    """

    def __init__(self, error_patterns: list[str] | None = None):
        self.error_patterns = error_patterns or []

    def _build_command(self, prompt: str, model: str | None,
                       args: list[str] | None = None) -> list[str]:
        effective_model = model or "gpt-5.3-codex"
        sandbox = "full-auto"
        # Disable sandbox in Docker (landlock doesn't work in containers)
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
        if args:
            cmd.extend(args)
        cmd.append(prompt)
        return cmd

    def run(self, prompt: str, model: str | None = None,
            args: list[str] | None = None) -> ExecutorResult:
        cmd = self._build_command(prompt, model, args)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,   # separate pipes — NOT merged
            text=True,
            start_new_session=True,
        )

        # Read stderr in a background thread for progress display
        stderr_result: dict = {"last_lines": [], "error": None}
        stderr_thread = threading.Thread(
            target=self._process_stderr,
            args=(proc.stderr, stderr_result),
            daemon=True,
        )
        stderr_thread.start()

        # Read stdout entirely as the final response
        stdout_content = ""
        stdout_error = None
        try:
            stdout_content = proc.stdout.read()
        except Exception as e:
            stdout_error = str(e)

        stderr_thread.join()
        proc.wait()

        # Determine final error
        error = None
        if stderr_result["error"]:
            error = stderr_result["error"]
        elif stdout_error:
            error = stdout_error
        elif proc.returncode != 0:
            tail = "\n".join(stderr_result["last_lines"])
            if tail:
                error = f"codex exited with code {proc.returncode}\nstderr: {tail}"
            else:
                error = f"codex exited with code {proc.returncode}"

        # Detect signals in stdout (the actual response)
        all_signals = parse_signals(stdout_content)

        # Check for error patterns
        if matched := check_error_patterns(stdout_content, self.error_patterns):
            return ExecutorResult(
                output=stdout_content,
                exit_code=proc.returncode,
                error=f"detected error pattern: {matched}",
                signals=all_signals,
            )

        return ExecutorResult(
            output=stdout_content,
            exit_code=proc.returncode,
            error=error,
            signals=all_signals,
        )

    def _process_stderr(self, stream, result: dict) -> None:
        """Read stderr line-by-line, filter for progress display.

        Shows header block (between first two "--------" separators)
        and bold summaries (**text**). Deduplicates lines.
        Captures last 5 lines for error context.
        """
        max_tail = 5
        header_count = 0
        seen: set[str] = set()
        tail: list[str] = []

        try:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue

                # Capture tail for error context
                stored = stripped[:256] + "..." if len(stripped) > 256 else stripped
                tail.append(stored)
                if len(tail) > max_tail:
                    tail.pop(0)

                # Filter logic matching Ralphex's shouldDisplay
                show = False
                filtered = line.rstrip("\n")
                skip_dedup = False

                if stripped.startswith("--------"):
                    header_count += 1
                    show = header_count <= 2
                    skip_dedup = True
                elif header_count == 1:
                    # Inside header block (between first two separators)
                    show = True
                elif stripped.startswith("**"):
                    # Bold summaries after header
                    show = True
                    filtered = strip_bold(stripped)

                if show:
                    if not skip_dedup:
                        if filtered in seen:
                            continue
                        seen.add(filtered)
                    print(filtered, flush=True)

        except Exception as e:
            result["error"] = str(e)

        result["last_lines"] = tail
