"""Executor pool — routes executor names to implementations."""

from __future__ import annotations

from pilot.executors.antigravity import AntigravityExecutor
from pilot.executors.claude import ClaudeExecutor
from pilot.executors.codex import CodexExecutor
from pilot.executors.gemini import GeminiExecutor
from pilot.executors.generic import GenericExecutor
from pilot.executors.opencode import OpenCodeExecutor
from pilot.executors.result import ExecutorResult
from pilot.executors.shell import ShellExecutor


class ExecutorPool:
    """Cached executor instances. Routes executor name to the right class.

    Routing:
      - "shell"       -> ShellExecutor    (runs commands, prompt = command)
      - "claude-code" -> ClaudeExecutor   (JSON stream)
      - "codex"       -> CodexExecutor    (split stderr/stdout)
      - "gemini"      -> GeminiExecutor   (JSON stream, yolo mode)
      - "antigravity" -> AntigravityExecutor (agy CLI, plain-text --print mode)
      - "opencode"    -> OpenCodeExecutor (opencode.ai, dangerous mode)
      - anything else -> GenericExecutor  (plain text)
    """

    def __init__(self):
        self._pool: dict = {}

    def get(self, executor_name: str):
        if executor_name not in self._pool:
            self._pool[executor_name] = self._create(executor_name)
        return self._pool[executor_name]

    @staticmethod
    def _create(name: str):
        if name == "shell":
            return ShellExecutor()
        if name == "claude-code":
            return ClaudeExecutor()
        if name == "codex":
            return CodexExecutor()
        if name == "gemini":
            return GeminiExecutor()
        if name == "antigravity":
            return AntigravityExecutor()
        if name == "opencode":
            return OpenCodeExecutor()
        return GenericExecutor(tool=name)
