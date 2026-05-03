"""Gemini CLI executor — streaming JSON events from gemini CLI."""

from __future__ import annotations

import json
import subprocess
import threading
import time

from pilot.signals import SignalScanner
from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog


def _extract_text(event: dict) -> str:
    """Extract assistant text content from a gemini stream-json event."""
    if event.get("type") != "message":
        return ""
    if event.get("role") != "assistant":
        return ""
    return event.get("content", "")


class GeminiExecutor:
    """Runs gemini CLI with streaming JSON parsing."""

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel: threading.Event | None = None) -> ExecutorResult:
        cmd = [
            "gemini", "--approval-mode", "yolo",
            # Required for headless/automated runs in untrusted folders
            # (added by Google in April 2026 alongside the CVSS-10 RCE fix).
            # Without this, gemini refuses to operate when invoked from a
            # directory the user hasn't interactively trusted.
            "--skip-trust",
            "--output-format", "stream-json",
        ]
        if model:
            cmd.extend(["-m", model])
        cmd.extend(["-p", prompt])

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
        terminal_signal_at = None
        grace_seconds = 60

        try:
            for line in proc.stdout:
                # Grace period: let process finish after terminal signal
                if terminal_signal_at is not None:
                    if time.monotonic() - terminal_signal_at > grace_seconds:
                        break
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                    text = _extract_text(event)
                    if text:
                        output_parts.append(text)
                        if on_output:
                            on_output(text)
                        for sig in scanner.feed(text):
                            all_signals.append(sig)
                            if on_signal:
                                on_signal(sig)
                            if sig.name in ("completed", "failed", "done") and terminal_signal_at is None:
                                terminal_signal_at = time.monotonic()
                except json.JSONDecodeError:
                    output_parts.append(line)
                    if on_output:
                        on_output(line)
                    for sig in scanner.feed(line):
                        all_signals.append(sig)
                        if on_signal:
                            on_signal(sig)
                        if sig.name in ("completed", "failed", "done") and terminal_signal_at is None:
                            terminal_signal_at = time.monotonic()
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
