"""Codex executor — streaming JSONL events via --json mode."""

from __future__ import annotations

import json
import os
import subprocess
import threading

from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog
from pilot.signals import SignalScanner


def _extract_text(event: dict) -> str | None:
    """Extract agent message text from a codex JSONL event.

    Returns the text for agent_message item.completed events,
    None for everything else.
    """
    if event.get("type") != "item.completed":
        return None
    item_type = event.get("item", {}).get("type")
    if item_type != "agent_message":
        return None
    return event.get("item", {}).get("text", "")


def _extract_progress(event: dict) -> str | None:
    """Extract a human-readable progress line from non-message events."""
    etype = event.get("type", "")
    item = event.get("item", {})
    itype = item.get("type", "")

    if etype == "item.completed" and itype == "command_execution":
        cmd = item.get("command", "")
        status = item.get("status", "")
        code = item.get("exit_code")
        suffix = f" (exit {code})" if code is not None else ""
        return f"$ {cmd} [{status}{suffix}]"

    if etype == "item.completed" and itype == "file_change":
        changes = item.get("changes", [])
        parts = [f"{c.get('kind', '?')} {c.get('path', '?')}" for c in changes]
        return "files: " + ", ".join(parts) if parts else None

    if etype == "item.started" and itype == "command_execution":
        cmd = item.get("command", "")
        return f"$ {cmd}"

    return None


class CodexExecutor:
    """Runs codex CLI with --json mode for structured JSONL output.

    All events arrive on stdout as JSONL. Agent messages contain the
    model's response text (including signals). stderr is only used
    for codex internal logging/errors.
    """

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel=None) -> ExecutorResult:
        effective_model = model or "o3"
        use_docker = os.environ.get("PILOT_DOCKER") == "1"

        cmd = ["codex", "exec", "--json"]
        if use_docker:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            cmd.append("--full-auto")
        cmd += [
            "--skip-git-repo-check",
            "-c", f'model="{effective_model}"',
            "-c", "model_reasoning_effort=xhigh",
            "-c", "stream_idle_timeout_ms=3600000",
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        # Send prompt via stdin (avoids shell escaping issues with large prompts)
        if proc.stdin:
            proc.stdin.write(prompt)
            proc.stdin.close()

        start_cancel_watchdog(cancel, proc)

        # Capture stderr tail for error reporting
        stderr_result: dict = {"last_lines": [], "error": None}
        stderr_thread = threading.Thread(
            target=self._capture_stderr,
            args=(proc.stderr, stderr_result),
            daemon=True,
        )
        stderr_thread.start()

        output_parts: list[str] = []
        all_signals = []
        stdout_error = None
        scanner = SignalScanner(known_signals)

        try:
            for line in proc.stdout:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Agent message — extract text, scan for signals
                text = _extract_text(event)
                if text:
                    output_parts.append(text)
                    if on_output:
                        on_output(text)
                    for sig in scanner.feed(text):
                        all_signals.append(sig)
                        if on_signal:
                            on_signal(sig)
                    continue

                # Other events — show progress
                progress = _extract_progress(event)
                if progress and on_output:
                    on_output(progress)

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

        stdout_content = "".join(output_parts)

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
    def _capture_stderr(stream, result: dict) -> None:
        """Capture stderr tail for error reporting."""
        max_tail = 10
        tail: list[str] = []

        try:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                stored = stripped[:256] + "..." if len(stripped) > 256 else stripped
                tail.append(stored)
                if len(tail) > max_tail:
                    tail.pop(0)
        except Exception as e:
            result["error"] = str(e)

        result["last_lines"] = tail
