"""Claude Code executor — streaming JSON events from claude CLI."""

from __future__ import annotations

import json
import os
import signal
import subprocess

from pilot.signals import Signal, parse_signals
from pilot.executors.result import ExecutorResult


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
            on_signal: callable = None) -> ExecutorResult:
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

        output_parts: list[str] = []
        all_signals: list[Signal] = []

        try:
            for line in proc.stdout:
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                    text = _extract_text(event)
                    if text:
                        output_parts.append(text)
                        if on_output:
                            on_output(text)
                        for sig in parse_signals(text, known_signals):
                            all_signals.append(sig)
                            if on_signal:
                                on_signal(sig)
                except json.JSONDecodeError:
                    output_parts.append(line)
                    if on_output:
                        on_output(line)
                    for sig in parse_signals(line, known_signals):
                        all_signals.append(sig)
                        if on_signal:
                            on_signal(sig)

            proc.wait()
        except KeyboardInterrupt:
            _kill_process_group(proc)
            raise

        full_output = "".join(output_parts)

        return ExecutorResult(
            output=full_output,
            exit_code=proc.returncode,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            signals=all_signals,
        )


def _kill_process_group(proc: subprocess.Popen) -> None:
    """Graceful shutdown: SIGTERM -> wait -> SIGKILL."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
