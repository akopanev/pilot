"""Claude Code executor — streaming JSON events from claude CLI."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time

from pilot.signals import SignalScanner
from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog


def _filter_env(*keys_to_remove: str) -> dict[str, str]:
    """Return current environment with specified keys removed."""
    return {k: v for k, v in os.environ.items() if k not in keys_to_remove}


def _extract_text(event: dict) -> str:
    """Extract text content from a claude stream-json event."""
    event_type = event.get("type", "")

    if event_type == "assistant":
        texts = []
        for c in event.get("message", {}).get("content", []):
            if c.get("type") == "text" and c.get("text"):
                texts.append(c["text"])
        return "".join(texts)

    if event_type == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta":
            return delta.get("text", "")

    if event_type == "message_stop":
        for c in event.get("message", {}).get("content", []):
            if c.get("type") == "text":
                return c.get("text", "")

    if event_type == "result":
        raw = event.get("result")
        if isinstance(raw, dict):
            return raw.get("output", "")

    return ""


class ClaudeExecutor:
    """Runs claude CLI with streaming JSON parsing."""

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel: threading.Event | None = None) -> ExecutorResult:
        cmd = [
            "claude", "--dangerously-skip-permissions",
            "--output-format", "stream-json", "--verbose",
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["-p", prompt])

        env = _filter_env("ANTHROPIC_API_KEY")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
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
