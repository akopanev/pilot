"""Claude Code executor — parses streaming JSON events from claude CLI."""

from __future__ import annotations

import json
import os
import signal
import subprocess

from pilot.signals import parse_signals
from pilot.executors.result import ExecutorResult, check_error_patterns, write_file


def filter_env(*keys_to_remove: str) -> list[str]:
    """Return current environment with specified keys removed."""
    return [
        entry for entry in (f"{k}={v}" for k, v in os.environ.items())
        if not any(entry.startswith(key + "=") for key in keys_to_remove)
    ]


def extract_text(event: dict) -> str:
    """Extract text content from a claude stream-json event.

    Handles event types:
      - "assistant": message.content[] array with text blocks
      - "content_block_delta": delta.text when delta.type == "text_delta"
      - "message_stop": final message.content[] text blocks
      - "result": object with "output" field (skip string results — already streamed)
    """
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
        raw_result = event.get("result")
        if raw_result is None:
            return ""
        # string result = session summary, skip (content already streamed)
        if isinstance(raw_result, str):
            return ""
        # object with "output" field
        if isinstance(raw_result, dict):
            return raw_result.get("output", "")

    return ""


class ClaudeExecutor:
    """Runs claude CLI with streaming JSON parsing.

    Matches Ralphex's ClaudeExecutor: spawns `claude --output-format stream-json`,
    parses JSON events line-by-line, extracts text, detects signals mid-stream.
    """

    def __init__(self, error_patterns: list[str] | None = None):
        self.error_patterns = error_patterns or []

    def _build_command(self, prompt: str, model: str | None,
                       args: list[str] | None = None) -> list[str]:
        cmd = [
            "claude", "--dangerously-skip-permissions",
            "--output-format", "stream-json", "--verbose",
        ]
        if model:
            cmd.extend(["--model", model])
        if args:
            cmd.extend(args)
        cmd.extend(["-p", prompt])
        return cmd

    def run(self, prompt: str, model: str | None = None,
            args: list[str] | None = None) -> ExecutorResult:
        cmd = self._build_command(prompt, model, args)

        # Filter ANTHROPIC_API_KEY from environment (claude uses different auth)
        env = filter_env("ANTHROPIC_API_KEY")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout like Ralphex
            text=True,
            env=dict(entry.split("=", 1) for entry in env) if env else None,
            start_new_session=True,
        )

        output_parts: list[str] = []
        all_signals: list[Signal] = []

        try:
            for line in proc.stdout:
                if not line.strip():
                    continue

                # Try to parse as JSON stream event
                try:
                    event = json.loads(line)
                    text = extract_text(event)
                    if text:
                        print(text, end="", flush=True)
                        output_parts.append(text)

                        # Detect XML signals in extracted text
                        for sig in parse_signals(text):
                            all_signals.append(sig)
                            if sig.type == "update":
                                write_file(sig.path, sig.payload)
                except json.JSONDecodeError:
                    # Non-JSON lines printed as-is (e.g., startup messages)
                    print(line, end="", flush=True)
                    output_parts.append(line)

                    for sig in parse_signals(line):
                        all_signals.append(sig)
                        if sig.type == "update":
                            write_file(sig.path, sig.payload)

            proc.wait()
        except KeyboardInterrupt:
            self._kill_process_group(proc)
            raise

        full_output = "".join(output_parts)

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

    @staticmethod
    def _kill_process_group(proc: subprocess.Popen) -> None:
        """Graceful shutdown: SIGTERM → wait → SIGKILL."""
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
