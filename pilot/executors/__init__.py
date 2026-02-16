"""Executor pool — routes tools to the correct executor implementation."""

from __future__ import annotations

from pilot.executors.claude import ClaudeExecutor
from pilot.executors.codex import CodexExecutor
from pilot.executors.custom import CustomExecutor
from pilot.executors.generic import GenericExecutor
from pilot.executors.shell import ShellExecutor
from pilot.executors.result import ExecutorResult


class ExecutorPool:
    """One executor instance per tool name, cached.

    Tool routing:
      - "claude-code" → ClaudeExecutor (JSON stream parsing)
      - "codex"       → CodexExecutor  (split stderr/stdout)
      - "shell"       → ShellExecutor  (subprocess.run)
      - anything else → GenericExecutor (plain-text streaming)
    """

    def __init__(self, error_patterns: list[str] | None = None):
        self._pool: dict[str, ClaudeExecutor | CodexExecutor | CustomExecutor | GenericExecutor] = {}
        self._error_patterns = error_patterns or []

    def get(self, tool: str, script: str | None = None) -> ClaudeExecutor | CodexExecutor | ShellExecutor | CustomExecutor | GenericExecutor:
        if tool == "shell":
            return ShellExecutor()
        cache_key = f"custom:{script}" if tool == "custom" and script else tool
        if cache_key not in self._pool:
            self._pool[cache_key] = self._create(tool, script=script)
        return self._pool[cache_key]

    def _create(self, tool: str, script: str | None = None) -> ClaudeExecutor | CodexExecutor | CustomExecutor | GenericExecutor:
        if tool == "claude-code":
            return ClaudeExecutor(error_patterns=self._error_patterns)
        if tool == "codex":
            return CodexExecutor(error_patterns=self._error_patterns)
        if tool == "custom":
            if not script:
                raise ValueError("tool='custom' requires a 'script' path")
            return CustomExecutor(script=script, error_patterns=self._error_patterns)
        # Any other tool (opencode, aider, etc.) — plain text streaming
        return GenericExecutor(tool=tool, error_patterns=self._error_patterns)
