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

    vars_raw = data.get("vars", {})
    if not isinstance(vars_raw, dict):
        raise ConfigError(f"{label}: 'vars' must be a mapping")
    runner_vars = {str(k): str(v) for k, v in vars_raw.items()}

    args_raw = data.get("args", [])
    if not isinstance(args_raw, list):
        raise ConfigError(f"{label}: 'args' must be a list of CLI tokens")
    for a in args_raw:
        if isinstance(a, (dict, list)):
            raise ConfigError(
                f"{label}: 'args' must be a list of scalars, got {type(a).__name__}"
            )
    runner_args = [str(a) for a in args_raw]
    if runner_args and executor == "shell":
        raise ConfigError(
            f"{label}: 'args' is not supported for the shell executor "
            f"(put flags inside 'command')"
        )

    return Runner(executor=executor, model=model, command=command,
                  vars=runner_vars, args=runner_args)


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

    runner_data = data.get("runner")
    runners_data = data.get("runners")

    if runner_data and runners_data:
        raise ConfigError(
            f"Stage '{name}': cannot have both 'runner' and 'runners' — pick one"
        )
    if not runner_data and not runners_data:
        raise ConfigError(f"Stage '{name}': must specify 'runner' or 'runners'")

    runner: Runner | None = None
    runners: list[Runner] | None = None
    fallback_runner: Runner | None = None
    is_ensemble = runners_data is not None

    if is_ensemble:
        if not isinstance(runners_data, list) or not runners_data:
            raise ConfigError(
                f"Stage '{name}': 'runners' must be a non-empty list"
            )
        runners = []
        for i, rd in enumerate(runners_data):
            r = _parse_runner(rd, f"Stage '{name}' runners[{i}]")
            if r.executor == "shell":
                raise ConfigError(
                    f"Stage '{name}' runners[{i}]: 'shell' executor is not allowed "
                    f"in ensemble runners"
                )
            runners.append(r)

        prompt = data.get("prompt")
        if not prompt:
            raise ConfigError(
                f"Stage '{name}': 'prompt' is required for ensemble stages"
            )

        if data.get("fallback_runner"):
            raise ConfigError(
                f"Stage '{name}': 'fallback_runner' is not supported on ensemble stages"
            )
    else:
        runner = _parse_runner(runner_data, f"Stage '{name}' runner")
        prompt = data.get("prompt")
        if runner.executor != "shell" and not prompt:
            raise ConfigError(
                f"Stage '{name}': 'prompt' is required for {runner.executor}"
            )
        fallback_data = data.get("fallback_runner")
        fallback_runner = (
            _parse_runner(fallback_data, f"Stage '{name}' fallback_runner")
            if fallback_data else None
        )

    parallel = bool(data.get("parallel", True))
    min_success = data.get("min_success")
    per_runner_timeout = data.get("per_runner_timeout")

    if is_ensemble:
        if min_success is not None:
            if not isinstance(min_success, int) or min_success < 1 or min_success > len(runners):
                raise ConfigError(
                    f"Stage '{name}': 'min_success' must be an int in 1..{len(runners)}"
                )
        if per_runner_timeout is not None:
            if not isinstance(per_runner_timeout, int) or per_runner_timeout < 1:
                raise ConfigError(
                    f"Stage '{name}': 'per_runner_timeout' must be a positive int (seconds)"
                )
    else:
        if min_success is not None or per_runner_timeout is not None or "parallel" in data:
            raise ConfigError(
                f"Stage '{name}': 'parallel'/'min_success'/'per_runner_timeout' "
                f"only apply to ensemble stages"
            )

    on_signal_data = data.get("on_signal", {})
    if not isinstance(on_signal_data, dict):
        raise ConfigError(f"Stage '{name}': 'on_signal' must be a mapping")

    on_signal: dict[str, Transition] = {}
    for sig_name, trans_data in on_signal_data.items():
        on_signal[sig_name] = _parse_transition(trans_data, sig_name, name)

    if "default" not in on_signal:
        raise ConfigError(f"Stage '{name}': 'on_signal' must include a 'default' entry")

    if is_ensemble:
        non_default = sorted(set(on_signal.keys()) - {"default"})
        if non_default:
            raise ConfigError(
                f"Stage '{name}': ensemble stages support only 'default' in 'on_signal' "
                f"(got: {non_default}); route via the next stage's signals instead"
            )

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
        runners=runners,
        parallel=parallel,
        min_success=min_success,
        per_runner_timeout=per_runner_timeout,
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
