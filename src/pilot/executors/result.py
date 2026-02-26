"""Shared types for all executors."""

from __future__ import annotations

from dataclasses import dataclass, field

from pilot.signals import Signal


@dataclass
class ExecutorResult:
    output: str
    exit_code: int
    error: str | None
    signals: list[Signal] = field(default_factory=list)
