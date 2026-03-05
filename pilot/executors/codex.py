"""Codex executor — separate stderr (progress) / stdout (response)."""

from __future__ import annotations

import os
import subprocess
import threading

from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog
from pilot.signals import SignalScanner


class CodexExecutor:
    """Runs codex CLI with split stderr/stdout handling.

    stderr: progress display (filtered).
    stdout: the actual response.
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None) -> ExecutorResult:
        effective_model = model or "o3"
        sandbox = "full-auto"
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
        cmd.append(prompt)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        start_cancel_watchdog(cancel, proc)

        stderr_result: dict = {"last_lines": [], "error": None}
        stderr_thread = threading.Thread(
            target=self._process_stderr,
            args=(proc.stderr, stderr_result, on_output),
            daemon=True,
        )
        stderr_thread.start()

        stdout_parts: list[str] = []
        all_signals = []
        stdout_error = None
        scanner = SignalScanner(known_signals)

        try:
            for line in proc.stdout:
                stdout_parts.append(line)
                if on_output:
                    on_output(line)
                for sig in scanner.feed(line):
                    all_signals.append(sig)
                    if on_signal:
                        on_signal(sig)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            stdout_error = str(e)
        finally:
            if proc.poll() is None:
                kill_process_group(proc)
            stderr_thread.join(timeout=5)
            proc.wait()

        # Flush remaining buffered signals
        for sig in scanner.flush():
            all_signals.append(sig)
            if on_signal:
                on_signal(sig)

        stdout_content = "".join(stdout_parts)

        error = None
        if stderr_result["error"]:
            error = stderr_result["error"]
        elif stdout_error:
            error = stdout_error
        elif proc.returncode != 0:
            tail = "\n".join(stderr_result["last_lines"])
            error = f"codex exited with code {proc.returncode}"
            if tail:
                error += f"\nstderr: {tail}"

        return ExecutorResult(
            output=stdout_content,
            exit_code=proc.returncode,
            error=error,
            signals=all_signals,
        )

    @staticmethod
    def _process_stderr(stream, result: dict,
                        on_output: callable = None) -> None:
        """Read stderr for progress display only.

        Signals are never parsed from stderr — codex echoes the prompt on
        stderr, which would cause false signal detections from examples
        in the prompt text.  Only stdout (the actual response) is parsed.
        """
        max_tail = 5
        tail: list[str] = []

        try:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                stored = stripped[:256] + "..." if len(stripped) > 256 else stripped
                if on_output:
                    on_output(stored)
                tail.append(stored)
                if len(tail) > max_tail:
                    tail.pop(0)
        except Exception as e:
            result["error"] = str(e)

        result["last_lines"] = tail
