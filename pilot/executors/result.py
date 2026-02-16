"""Shared types and helpers for all executors."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from pilot.signals import Signal


@dataclass
class ExecutorResult:
    output: str
    exit_code: int
    error: str | None
    signals: list[Signal] = field(default_factory=list)


def check_error_patterns(output: str, patterns: list[str]) -> str | None:
    """Case-insensitive substring check for known error patterns."""
    output_lower = output.lower()
    for pattern in patterns:
        if pattern.strip() and pattern.lower() in output_lower:
            return pattern
    return None


def write_file(path: str, content: str) -> None:
    """Write content to path, creating directories as needed."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
