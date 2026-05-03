"""Data models for pipeline configuration and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field


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
    prompt: str | None                          # AI stages (supports {{file:}})
    runner: Runner | None                        # single-runner stages
    fallback_runner: Runner | None
    on_signal: dict[str, Transition]            # signal_name -> Transition
    pre_step: str | None = None                 # shell command before executor
    post_step: str | None = None                # shell command after executor
    runners: list[Runner] | None = None         # ensemble stages (parallel runners)
    parallel: bool = True                       # ensemble: run runners concurrently
    min_success: int | None = None              # ensemble: K-of-N success threshold
    per_runner_timeout: int | None = None       # ensemble: per-runner cancel deadline (s)

    @property
    def is_ensemble(self) -> bool:
        return self.runners is not None


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
