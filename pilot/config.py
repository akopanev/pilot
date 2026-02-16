"""YAML config parsing, defaults, validation."""

from __future__ import annotations

import os

import yaml

from pilot.agents import load_agents, load_builtin_agents, parse_yaml_agents
from pilot.models import (
    AgentDef,
    AgentDefaults,
    AgentStep,
    GateStep,
    LoopStep,
    PilotConfig,
    ShellStep,
    Step,
)


class ConfigError(Exception):
    pass


def validate_version(raw: dict) -> None:
    version = raw.get("version")
    if not version:
        raise ConfigError("Missing 'version' field in config")
    if str(version) not in ("1.0", "1"):
        raise ConfigError(f"Unsupported config version: {version}")


def parse_defaults(raw: dict) -> AgentDefaults:
    agent = raw.get("agent", {})
    return AgentDefaults(
        tool=agent.get("tool", "claude-code"),
        model=agent.get("model", "claude-sonnet-4"),
        retry=agent.get("retry", 0),
        args=agent.get("args", []),
    )


def parse_step(raw: dict) -> Step:
    step_id = raw.get("id")
    if not step_id:
        raise ConfigError("Step missing 'id' field")

    if "agent" in raw:
        agent = raw["agent"]
        if isinstance(agent, str):
            # shorthand: agent: @name (reference) or agent: prompts/task.md (file)
            return AgentStep(id=step_id, prompt=agent)
        _AGENT_KEYS = {"prompt", "tool", "model", "script", "retry", "args"}
        unknown = set(agent.keys()) - _AGENT_KEYS
        if unknown:
            raise ConfigError(
                f"Step '{step_id}': unknown agent key(s): {', '.join(sorted(unknown))}"
            )
        return AgentStep(
            id=step_id,
            prompt=agent.get("prompt", ""),
            tool=agent.get("tool"),
            model=agent.get("model"),
            script=agent.get("script"),
            retry=agent.get("retry"),
            args=agent.get("args"),
        )
    elif "shell" in raw:
        shell = raw["shell"]
        if isinstance(shell, str):               # shorthand: shell: npm test
            return ShellStep(id=step_id, command=shell)
        return ShellStep(id=step_id, command=shell["command"])
    elif "loop" in raw:
        return parse_loop_step(raw)
    elif "gate" in raw:
        return GateStep(id=step_id)
    else:
        raise ConfigError(f"Unknown step type for '{step_id}'")


def parse_loop_step(raw: dict) -> LoopStep:
    step_id = raw["id"]
    loop_config = raw["loop"]

    # Parse child steps
    child_steps = [parse_step(s) for s in raw.get("steps", [])]

    return LoopStep(
        id=step_id,
        steps=child_steps,
        over=loop_config.get("over"),
        as_var=loop_config.get("as"),
        order=loop_config.get("order", "asc"),
        until=loop_config.get("until"),
        max_rounds=loop_config.get("max_rounds", 5),
    )


def parse_steps(raw_steps: list[dict]) -> list[Step]:
    return [parse_step(s) for s in raw_steps]


def _collect_ids(steps: list[Step]) -> list[str]:
    """Recursively collect all step IDs."""
    ids: list[str] = []
    for step in steps:
        ids.append(step.id)
        if isinstance(step, LoopStep):
            ids.extend(_collect_ids(step.steps))
    return ids


def validate_pipeline(steps: list[Step]) -> None:
    """Validate pipeline structure beyond parsing."""
    ids = _collect_ids(steps)

    # Duplicate IDs
    seen: set[str] = set()
    for step_id in ids:
        if step_id in seen:
            raise ConfigError(f"Duplicate step id: '{step_id}'")
        seen.add(step_id)

    _validate_steps(steps)


def _validate_steps(steps: list[Step]) -> None:
    """Recursively validate step constraints."""
    for step in steps:
        if isinstance(step, LoopStep):
            if not step.over and not step.until:
                raise ConfigError(
                    f"Loop '{step.id}' must have 'over' or 'until'"
                )
            if step.over and not step.as_var:
                raise ConfigError(
                    f"Iterator loop '{step.id}' requires 'as' variable"
                )
            if not step.steps:
                raise ConfigError(f"Loop '{step.id}' has no child steps")
            _validate_steps(step.steps)
        elif isinstance(step, AgentStep):
            if step.tool == "custom" and not step.script:
                raise ConfigError(
                    f"Step '{step.id}' uses tool='custom' but no 'script' provided"
                )


def resolve_agent_refs(steps: list[Step], agents: dict[str, AgentDef]) -> None:
    """Recursively resolve @agent references in pipeline steps.

    For each AgentStep where prompt starts with '@', look up the named agent
    and apply its prompt/tool/model/script/retry as base values. Step-level
    fields (if set) override the agent's values.
    """
    for step in steps:
        if isinstance(step, LoopStep):
            resolve_agent_refs(step.steps, agents)
        elif isinstance(step, AgentStep) and step.prompt.startswith("@"):
            name = step.prompt[1:]  # strip @
            if name not in agents:
                raise ConfigError(f"Step '{step.id}' references unknown agent '@{name}'")
            agent = agents[name]
            # Agent provides base, step overrides
            step.prompt = agent.prompt
            if step.tool is None:
                step.tool = agent.tool
            if step.model is None:
                step.model = agent.model
            if step.script is None:
                step.script = agent.script
            if step.retry is None:
                step.retry = agent.retry
            if step.args is None:
                step.args = agent.args


def load_config(path: str) -> PilotConfig:
    """Load and validate pipeline.yaml."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ConfigError(f"Empty config file: {path}")

    validate_version(raw)

    # Derive project_dir: if config is in .pilot/, project is the parent.
    # Otherwise, project is the config's directory (backward compat).
    config_dir = os.path.dirname(os.path.abspath(path))
    if os.path.basename(config_dir) == ".pilot":
        project_dir = os.path.dirname(config_dir)
    else:
        project_dir = config_dir

    # Load agents: YAML section > file-based (.pilot/agents/) > built-ins
    builtin_agents = load_builtin_agents()
    file_agents = load_agents(project_dir)
    yaml_agents = parse_yaml_agents(raw.get("agents", {}))
    # built-in < file-based < YAML (each layer overrides)
    merged_agents = {**builtin_agents, **file_agents, **yaml_agents}

    steps = parse_steps(raw.get("pipeline", []))
    resolve_agent_refs(steps, merged_agents)
    validate_pipeline(steps)

    raw_defaults = raw.get("defaults", {})

    return PilotConfig(
        version=str(raw["version"]),
        inputs=raw.get("inputs", {}),
        defaults=parse_defaults(raw_defaults),
        pipeline=steps,
        agents=merged_agents,
        error_patterns=raw_defaults.get("error_patterns", []),
        iteration_delay_ms=raw_defaults.get("iteration_delay_ms", 2000),
    )
