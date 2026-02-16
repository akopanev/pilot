"""Data classes for pipeline steps and runtime context."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentStep:
    id: str
    prompt: str                   # prompt file path OR inline text
    tool: str | None = None       # override defaults.agent.tool
    model: str | None = None      # override defaults.agent.model
    script: str | None = None     # custom script path (tool="custom")
    retry: int | None = None      # per-step retry override
    args: list[str] | None = None # extra CLI args for the executor


@dataclass
class ShellStep:
    id: str
    command: str


@dataclass
class GateStep:
    id: str


@dataclass
class LoopStep:
    id: str
    steps: list[Step]             # child steps (may contain nested LoopSteps)

    # Iterator loop (one of these sets):
    over: str | None = None       # folder path or variable reference
    as_var: str | None = None     # inject file contents as {{AS_VAR}}
    order: str = "asc"            # asc or desc

    # Convergence loop:
    until: str | None = None      # signal name (e.g., "APPROVE")
    max_rounds: int = 5           # safety limit


Step = AgentStep | ShellStep | GateStep | LoopStep


@dataclass
class AgentDef:
    """A reusable named agent definition."""
    name: str
    prompt: str                   # prompt text or file path
    tool: str | None = None       # override defaults.agent.tool
    model: str | None = None      # override defaults.agent.model
    script: str | None = None     # custom script path (tool="custom")
    retry: int | None = None      # per-step retry override
    args: list[str] | None = None # extra CLI args for the executor
    source: str | None = None     # where this agent was loaded from


@dataclass
class AgentDefaults:
    tool: str = "claude-code"
    model: str = "claude-sonnet-4"
    retry: int = 0
    args: list[str] = field(default_factory=list)


@dataclass
class PilotConfig:
    version: str
    inputs: dict[str, str]
    defaults: AgentDefaults
    pipeline: list[Step]
    agents: dict[str, AgentDef] = field(default_factory=dict)
    error_patterns: list[str] = field(default_factory=list)
    iteration_delay_ms: int = 2000


@dataclass
class QAPair:
    """A question asked by a step and the user's answer."""
    step_id: str
    question: str
    answer: str


@dataclass
class RuntimeContext:
    project_dir: str              # workspace root (cwd)
    config_dir: str               # directory containing pipeline.yaml (for path resolution)
    default_branch: str
    progress_path: str
    diff_command: str
    round: int = 0
    emissions: dict[str, str] = field(default_factory=dict)
    questions: list[QAPair] = field(default_factory=list)
    debug: bool = False
    debug_truncate: int = 80
