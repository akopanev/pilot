"""Antigravity CLI executor — plain-text streaming from the `agy` CLI.

Antigravity CLI (binary: `agy`, v1.0.4) is Google's successor to Gemini CLI
(consumer Gemini CLI stops serving 2026-06-18). Its headless interface follows
Claude Code conventions, NOT Gemini's:

  - `--print` TAKES A VALUE (the prompt). It is NOT a boolean mode flag: the
    token right after `--print` is consumed as the prompt. Therefore `--print`
    must be the LAST flag and the prompt its value — e.g.
    `agy <flags> --print "<prompt>"`. The earlier layout
    `agy --print --dangerously-skip-permissions ... <prompt>` silently fed
    `--dangerously-skip-permissions` to `--print` as the prompt, so the skip
    flag never took effect (no tool perms → agy wrote no OUTPUT file and
    emitted nothing useful). Verified on v1.0.4.
  - `--dangerously-skip-permissions` auto-approves tools (required for our
    file-editing pipelines — agy writes the OUTPUT file via its own file tool),
    replacing gemini's `--approval-mode yolo`.
  - output is PLAIN TEXT on stdout — there is no `--output-format`/JSON mode.
  - per-invocation model IS supported as of v1.0.4: `--model "<name>"` where
    <name> is one of `agy models` (e.g. "Gemini 3.1 Pro (High)",
    "Claude Opus 4.6 (Thinking)", "GPT-OSS 120B (Medium)"). Reasoning effort is
    encoded in the name suffix — (Low)/(Medium)/(High)/(Thinking). `runner.model`
    is passed through verbatim to `--model`; if omitted, agy uses the global
    "model" in `~/.gemini/antigravity-cli/settings.json`. A short-slug alias map
    (see _MODEL_ALIASES) lets pipelines use `gemini-3.1-pro-high` style ids too.
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

# Convenience slugs → exact `agy models` names. Pipelines may set runner.model to
# either a slug here or the full agy name (passed through verbatim if not found).
# Run `agy models` to see the live list; effort is the (…) suffix.
_MODEL_ALIASES = {
    "gemini-3.5-flash": "Gemini 3.5 Flash (Medium)",
    "gemini-3.5-flash-low": "Gemini 3.5 Flash (Low)",
    "gemini-3.5-flash-high": "Gemini 3.5 Flash (High)",
    "gemini-3.1-pro": "Gemini 3.1 Pro (High)",
    "gemini-3.1-pro-low": "Gemini 3.1 Pro (Low)",
    "gemini-3.1-pro-high": "Gemini 3.1 Pro (High)",
    "claude-sonnet-4.6": "Claude Sonnet 4.6 (Thinking)",
    "claude-opus-4.6": "Claude Opus 4.6 (Thinking)",
    "gpt-oss-120b": "GPT-OSS 120B (Medium)",
}


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
        #
        # In Docker the container IS the sandbox: agy's trustedWorkspaces is
        # unreliable there (ends up empty regardless of init-docker), yet agy runs
        # in /workspace with --dangerously-skip-permissions and --print-timeout
        # bounds any hang — so skip this host-only guard. (Headless OAuth may still
        # fail for keychain-bound tokens; see antigravity-cli #57/#78.)
        in_docker = os.environ.get("PILOT_DOCKER") == "1"
        if not in_docker and not _is_trusted(cwd):
            raise RuntimeError(
                f"antigravity: workspace '{cwd}' is not trusted by agy, so "
                f"`agy --dangerously-skip-permissions` would hang. Trust it once "
                f"(open `agy` here interactively, or add the path to "
                f"\"trustedWorkspaces\" in {_SETTINGS_PATH})."
            )

        # Flags first; `--print <prompt>` LAST because `--print` consumes the
        # next token as the prompt value (see module docstring). Putting any flag
        # after `--print` would make that flag the prompt.
        cmd = [
            "agy",
            "--dangerously-skip-permissions",
            "--print-timeout", _PRINT_TIMEOUT,
        ]
        # Per-invocation model (v1.0.4+): map a known slug or pass through verbatim.
        if model:
            cmd += ["--model", _MODEL_ALIASES.get(model, model)]
        # Raw per-runner args, still before `--print`.
        if args:
            cmd += args
        cmd += ["--print", prompt]  # MUST be last: prompt is the value of --print

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
