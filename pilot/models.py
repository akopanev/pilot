"""Data models for pipeline configuration and runtime state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Runner:
    executor: str           # "shell", "claude-code", "codex", etc.
    model: str | None       # "opus", "o3", "sonnet" — AI executors
    command: str | None      # shell command/script — shell executor


@dataclass
class Transition:
    to: str | None          # target stage name, None = stop pipeline
    fail: bool = False      # True for __fail__ exits (preserve state)


@dataclass
class Stage:
    name: str
    prompt: str | None                      # AI stages (supports {{file:}})
    runner: Runner
    fallback_runner: Runner | None
    on_signal: dict[str, Transition]        # signal_name -> Transition
    pre_step: str | None = None             # shell command before executor
    post_step: str | None = None            # shell command after executor


@dataclass
class PipelineConfig:
    version: str
    vars: dict[str, str]                    # key=env var name, value=value
    stages: dict[str, Stage]                # ordered dict, first = entry
    start_stage: str                        # first key in stages
    pre_pipeline: str | None = None             # shell: setup (before main loop)
    on_pipeline_success: str | None = None      # shell: notify/chain (on success)
    on_pipeline_failure: str | None = None      # shell: alert (on failure)


@dataclass
class PipelineState:
    stage: str
