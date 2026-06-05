"""Antigravity CLI executor — plain-text streaming from the `agy` CLI.

Antigravity CLI (binary: `agy`, v1.0.0) is Google's successor to Gemini CLI
(consumer Gemini CLI stops serving 2026-06-18). Its headless interface follows
Claude Code conventions, NOT Gemini's:

  - prompt is a positional arg after `--print` (`--print`/`-p`/`--prompt` are a
    boolean mode flag, not a value holder).
  - `--dangerously-skip-permissions` auto-approves tools (required for our
    file-editing pipelines), replacing gemini's `--approval-mode yolo`.
  - output is PLAIN TEXT on stdout — there is no `--output-format`/JSON mode.
  - there is NO per-invocation model flag (`-m`/`--model` are rejected, env is
    ignored). The model is a global setting in
    `~/.gemini/antigravity-cli/settings.json` ("model" key; default
    gemini-3.5-flash). `runner.model` is therefore ignored here.
  - workspace trust is NOT a flag: the cwd must be in `trustedWorkspaces` in the
    global settings.json, otherwise `agy --dangerously-skip-permissions` HANGS
    waiting for interactive trust. We pre-flight that and fail fast instead.
  - `--print-timeout` defaults to 5m, too short for real agent runs — we raise it.
"""

from __future__ import annotations

import json
import os
import threading

import subprocess

from pilot.signals import SignalScanner
from pilot.executors.result import ExecutorResult, kill_process_group, start_cancel_watchdog

# agy reads/writes its global config here. trustedWorkspaces lives in this file.
_SETTINGS_PATH = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")

# Generous cap for long agent runs (Go duration string). agy's default is 5m.
_PRINT_TIMEOUT = "60m"


def _trusted_roots() -> list[str]:
    """Read trustedWorkspaces from agy's global settings.json (best-effort)."""
    try:
        with open(_SETTINGS_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    roots = data.get("trustedWorkspaces") or []
    return [os.path.realpath(os.path.expanduser(r)) for r in roots if isinstance(r, str)]


def _is_trusted(cwd: str) -> bool:
    """True if cwd equals or sits under a trusted workspace root."""
    cwd = os.path.realpath(cwd)
    for root in _trusted_roots():
        if cwd == root or cwd.startswith(root + os.sep):
            return True
    return False


class AntigravityExecutor:
    """Runs the `agy` CLI in headless (--print) mode with plain-text output."""

    def __init__(self):
        # Warn at most once per process about the ignored model selection.
        self._model_warned = False

    def run(self, prompt: str, model: str | None = None,
            known_signals: set[str] | None = None,
            on_output: callable = None,
            on_signal: callable = None,
            cancel: threading.Event | None = None,
            args: list[str] | None = None) -> ExecutorResult:
        cwd = os.getcwd()
        # Fail fast instead of hanging: agy --dangerously-skip-permissions blocks
        # forever in an untrusted workspace. TODO: optionally auto-add cwd to
        # trustedWorkspaces (decided against for now — don't mutate user config).
        if not _is_trusted(cwd):
            raise RuntimeError(
                f"antigravity: workspace '{cwd}' is not trusted by agy, so "
                f"`agy --dangerously-skip-permissions` would hang. Trust it once "
                f"(open `agy` here interactively, or add the path to "
                f"\"trustedWorkspaces\" in {_SETTINGS_PATH})."
            )

        # agy ignores per-invocation model selection; surface it once.
        if model and on_output and not self._model_warned:
            on_output(
                f"[antigravity] note: agy does not support per-run model "
                f"selection; '{model}' ignored. Set \"model\" in {_SETTINGS_PATH}."
            )
            self._model_warned = True

        cmd = [
            "agy", "--print",
            "--dangerously-skip-permissions",
            "--print-timeout", _PRINT_TIMEOUT,
        ]
        # Raw per-runner args before the positional prompt (which must be last).
        if args:
            cmd += args
        cmd.append(prompt)  # positional, must come after all flags

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

        try:
            # Plain text: every non-empty line is output. agy streams progress
            # lines as it works, then flushes the final answer.
            for line in proc.stdout:
                if not line.strip():
                    continue
                output_parts.append(line)
                if on_output:
                    on_output(line)
                for sig in scanner.feed(line):
                    all_signals.append(sig)
                    if on_signal:
                        on_signal(sig)
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
