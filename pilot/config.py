"""YAML config loader and validator."""

from __future__ import annotations

import os

import yaml

from pilot.models import PipelineConfig, Runner, Stage, Transition


class ConfigError(Exception):
    pass


def _parse_runner(data: dict, label: str) -> Runner:
    if not isinstance(data, dict):
        raise ConfigError(f"{label}: must be a mapping")
    executor = data.get("executor")
    if not executor:
        raise ConfigError(f"{label}: 'executor' is required")
    model = data.get("model")
    command = data.get("command")
    if executor == "shell" and not command:
        raise ConfigError(f"{label}: shell executor requires 'command'")
    return Runner(executor=executor, model=model, command=command)


def _parse_transition(data, signal_name: str, stage_name: str) -> Transition:
    if data is None or data == "__succeed__":
        return Transition(to=None, fail=False)
    if data == "__fail__":
        return Transition(to=None, fail=True)
    if isinstance(data, str):
        return Transition(to=data)
    raise ConfigError(
        f"Stage '{stage_name}' signal '{signal_name}': "
        f"must be a stage name, '__succeed__', '__fail__', or null"
    )


def _parse_stage(name: str, data: dict) -> Stage:
    if not isinstance(data, dict):
        raise ConfigError(f"Stage '{name}': must be a mapping")

    # Runner (parse first to know executor type)
    runner_data = data.get("runner")
    if not runner_data:
        raise ConfigError(f"Stage '{name}': 'runner' is required")
    runner = _parse_runner(runner_data, f"Stage '{name}' runner")

    # Prompt — required for AI executors, not needed for shell
    prompt = data.get("prompt")
    if runner.executor != "shell" and not prompt:
        raise ConfigError(f"Stage '{name}': 'prompt' is required for {runner.executor}")

    # Fallback runner (optional)
    fallback_data = data.get("fallback_runner")
    fallback_runner = _parse_runner(fallback_data, f"Stage '{name}' fallback_runner") if fallback_data else None

    # Transitions
    on_signal_data = data.get("on_signal", {})
    if not isinstance(on_signal_data, dict):
        raise ConfigError(f"Stage '{name}': 'on_signal' must be a mapping")

    on_signal: dict[str, Transition] = {}
    for sig_name, trans_data in on_signal_data.items():
        on_signal[sig_name] = _parse_transition(trans_data, sig_name, name)

    if "default" not in on_signal:
        raise ConfigError(f"Stage '{name}': 'on_signal' must include a 'default' entry")

    pre_step = data.get("pre_step")
    post_step = data.get("post_step")

    return Stage(
        name=name,
        prompt=prompt,
        runner=runner,
        fallback_runner=fallback_runner,
        on_signal=on_signal,
        pre_step=pre_step,
        post_step=post_step,
    )


def load_config(path: str) -> PipelineConfig:
    """Load and validate pipeline yaml."""
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

    version = str(raw.get("version", "0.1"))

    # Vars: key = env var name, value = value
    vars_raw = raw.get("vars", {})
    if not isinstance(vars_raw, dict):
        raise ConfigError("'vars' must be a mapping")
    config_vars = {str(k): str(v) for k, v in vars_raw.items()}

    stages_raw = raw.get("stages")
    if not isinstance(stages_raw, dict) or not stages_raw:
        raise ConfigError("'stages' must be a non-empty mapping")

    stages: dict[str, Stage] = {}
    for stage_name, stage_data in stages_raw.items():
        stages[stage_name] = _parse_stage(stage_name, stage_data)

    # Validate transitions point to existing stages
    all_stage_names = set(stages.keys())
    for stage in stages.values():
        for sig_name, transition in stage.on_signal.items():
            if transition.to and transition.to not in all_stage_names:
                raise ConfigError(
                    f"Stage '{stage.name}' signal '{sig_name}' transitions to "
                    f"unknown stage '{transition.to}'"
                )

    # Start stage: explicit or first in YAML
    start_stage = raw.get("starting")
    if start_stage:
        if start_stage not in all_stage_names:
            raise ConfigError(f"'starting' references unknown stage '{start_stage}'")
    else:
        start_stage = next(iter(stages))

    pre_pipeline = raw.get("pre_pipeline")
    on_pipeline_success = raw.get("on_pipeline_success")
    on_pipeline_failure = raw.get("on_pipeline_failure")

    return PipelineConfig(
        version=version,
        vars=config_vars,
        stages=stages,
        start_stage=start_stage,
        pre_pipeline=pre_pipeline,
        on_pipeline_success=on_pipeline_success,
        on_pipeline_failure=on_pipeline_failure,
    )
