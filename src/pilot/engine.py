"""Pipeline engine — config-driven state machine loop."""

from __future__ import annotations

import os
import sys
import threading

from pilot.display import Display
from pilot.executors import ExecutorPool
from pilot.models import PipelineConfig, PipelineState, Stage
from pilot.signals import BUILTIN_SIGNALS, parse_signals
from pilot.state import clear_state, read_state, write_state
from pilot.templates import TemplateError, resolve_templates
from pilot.vars import clear_vars, export_vars, write_var


class PipelineError(Exception):
    pass


class PipelineEngine:
    """State machine: load stage -> build prompt -> run executor -> route by signal."""

    def __init__(
        self,
        config: PipelineConfig,
        config_dir: str,
        state_path: str,
        vars_path: str,
        display: Display,
        cancel_event: threading.Event | None = None,
        delay: float = 2.0,
    ):
        self.config = config
        self.config_dir = config_dir
        self.state_path = state_path
        self.vars_path = vars_path
        self.display = display
        self.cancel = cancel_event or threading.Event()
        self.delay = delay
        self.executors = ExecutorPool()

        # Resume or start fresh
        saved = read_state(state_path)
        if saved and saved.stage in config.stages:
            self.state = saved
            self.display.info(
                f"[dim]Resuming[/] [stage]{saved.stage}[/] "
                f"[dim]round {saved.round}[/]"
            )
        else:
            self.state = PipelineState(
                stage=config.start_stage,
                round=0,
            )

    def _sync_env(self) -> None:
        """Export vars to file and os.environ.

        Writes config vars to the vars file, then loads everything
        (config + agent-emitted vars) into os.environ.
        """
        for key, value in self.config.vars.items():
            write_var(self.vars_path, key, value)

        export_vars(self.vars_path)

    def run(self) -> None:
        consecutive_failures = 0

        while not self.cancel.is_set():
            self.state.round += 1
            self._sync_env()

            stage = self.config.stages.get(self.state.stage)
            if not stage:
                self.display.error(f"Unknown stage: {self.state.stage}")
                sys.exit(1)

            self.display.round_header(
                self.state.round,
                stage.name,
                stage.runner.executor,
                stage.runner.model,
            )

            # Build prompt
            try:
                prompt = self._build_prompt(stage)
            except TemplateError as e:
                self.display.error(f"Template error: {e}")
                sys.exit(1)

            # Known signals for this stage
            known = set(stage.on_signal.keys()) | BUILTIN_SIGNALS

            # Run executor with retries, then fallback with retries
            result = self._run_with_retries(stage, prompt, known)

            if result.exit_code != 0:
                consecutive_failures += 1
                self.display.warn(
                    f"Round failed, "
                    f"consecutive failures {consecutive_failures}/3"
                )
                if consecutive_failures >= 3:
                    self.display.error("3 consecutive round failures. Stopping.")
                    sys.exit(1)
                self._wait()
                continue

            consecutive_failures = 0

            # Parse signals
            signals = result.signals or parse_signals(result.output, known)

            # Built-in: failed
            failed = next((s for s in signals if s.name == "failed"), None)
            if failed:
                self.display.error(f"Agent failed: {failed.content}")
                sys.exit(1)

            # Built-in: var — persist to vars file
            # Format: <signal:var key=NAME>value
            for s in signals:
                if s.name == "var" and "key" in s.attrs:
                    write_var(self.vars_path, s.attrs["key"], s.content)

            # Built-in: update — display progress
            for s in signals:
                if s.name == "update":
                    self.display.update(s.content)

            # Domain signal (first non-builtin)
            domain = next(
                (s for s in signals if s.name not in BUILTIN_SIGNALS),
                None,
            )
            if domain:
                self.display.domain_signal(domain.name, domain.content)

            # Route
            if domain and domain.name in stage.on_signal:
                transition = stage.on_signal[domain.name]
            elif "default" in stage.on_signal:
                transition = stage.on_signal["default"]
            else:
                self.display.error(f"No default in stage '{stage.name}'")
                sys.exit(1)

            # Transition
            if transition.to is None:
                self.display.done(domain.content if domain else "complete")
                clear_state(self.state_path)
                clear_vars(self.vars_path)
                break

            old_stage = self.state.stage
            self.state.stage = transition.to
            write_state(self.state_path, self.state)
            self.display.transition(old_stage, transition.to)
            self._wait()

    def _run_with_retries(self, stage: Stage, prompt: str,
                          known: set[str]) -> ExecutorResult:
        """Try primary runner twice, then fallback runner twice.

        Returns the first successful result, or the last failed result.
        """
        from pilot.executors.result import ExecutorResult

        runners = [(stage.runner, "primary")]
        if stage.fallback_runner:
            runners.append((stage.fallback_runner, "fallback"))

        result = None
        for runner, label in runners:
            executor = self.executors.get(runner.executor)
            for attempt in range(1, 3):
                result = executor.run(
                    prompt, model=runner.model, known_signals=known,
                )
                if result.exit_code == 0:
                    return result

                tag = f"{runner.executor}/{runner.model}"
                self.display.warn(
                    f"{label} {tag} failed "
                    f"(attempt {attempt}/2, exit {result.exit_code})"
                )
                if attempt < 2:
                    self._wait()

            # Switch to fallback
            if label == "primary" and stage.fallback_runner:
                fb = stage.fallback_runner
                self.display.fallback(
                    f"{runner.executor}/{runner.model}",
                    f"{fb.executor}/{fb.model}",
                )

        return result

    def _build_prompt(self, stage: Stage) -> str:
        """Build the text passed to the executor.

        Shell: runner.command (with {{file:}} resolution)
        AI:    stage.prompt  (with {{file:}} resolution)
        """
        if stage.runner.executor == "shell":
            raw = stage.runner.command or ""
        else:
            raw = stage.prompt or ""

        return resolve_templates(raw, self.config_dir, self.vars_path)

    def _wait(self) -> None:
        self.cancel.wait(timeout=self.delay)
