"""Pipeline engine — config-driven state machine loop."""

from __future__ import annotations

import subprocess
import threading
import time

from pilot.display import Display
from pilot.executors import ExecutorPool
from pilot.models import PipelineConfig, PipelineState, Stage
from rich.markup import escape as rich_escape

from pilot.signals import BUILTIN_SIGNALS
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
                f"[dim]Resuming[/] [stage]{saved.stage}[/]"
            )
        else:
            self.state = PipelineState(stage=config.start_stage)

    def _sync_env(self) -> None:
        """Export vars to file and os.environ.

        Writes config vars to the vars file, then loads everything
        (config + agent-emitted vars) into os.environ.
        """
        for key, value in self.config.vars.items():
            write_var(self.vars_path, key, value)

        export_vars(self.vars_path)

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        if seconds >= 3600:
            return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"
        if seconds >= 60:
            return f"{seconds // 60}m{seconds % 60:02d}s"
        return f"{seconds}s"

    def run(self) -> None:
        consecutive_failures = 0
        round_num = 0
        pipeline_start = time.monotonic()

        while not self.cancel.is_set():
            round_num += 1
            round_start = time.monotonic()
            self._sync_env()

            stage = self.config.stages.get(self.state.stage)
            if not stage:
                raise PipelineError(f"Unknown stage: {self.state.stage}")

            self.display.round_header(
                round_num,
                stage.name,
                stage.runner.executor,
                stage.runner.model,
            )

            # pre_step — shell command before main executor
            if stage.pre_step:
                pre_ok = self._run_step("pre_step", stage.pre_step)
                if not pre_ok:
                    consecutive_failures += 1
                    self.display.warn(
                        f"pre_step failed, "
                        f"consecutive failures {consecutive_failures}/3"
                    )
                    if consecutive_failures >= 3:
                        raise PipelineError("3 consecutive round failures")
                    self._wait()
                    continue

            # Build prompt
            try:
                prompt = self._build_prompt(stage)
            except TemplateError as e:
                raise PipelineError(f"Template error: {e}") from e

            # Known signals for this stage
            known = set(stage.on_signal.keys()) | BUILTIN_SIGNALS

            # Run executor with retries, then fallback with retries
            result = self._run_with_retries(stage, prompt, known)

            # post_step — shell command after main executor (always runs)
            if stage.post_step:
                post_ok = self._run_step("post_step", stage.post_step)
                if not post_ok:
                    self.display.warn("post_step failed (continuing)")

            elapsed = int(time.monotonic() - round_start)
            self.display.info(f"[dim]round {round_num} · {self._fmt_duration(elapsed)}[/]")

            if result.exit_code != 0:
                consecutive_failures += 1
                self.display.warn(
                    f"Round failed, "
                    f"consecutive failures {consecutive_failures}/3"
                )
                if consecutive_failures >= 3:
                    raise PipelineError("3 consecutive round failures")
                self._wait()
                continue

            consecutive_failures = 0

            # Signals already displayed in real-time via _on_signal callback
            signals = self._live_signals

            # Find first domain signal for routing
            domain = None
            for s in signals:
                if s.name not in ("var", "update"):
                    domain = s
                    break

            # Route
            if domain and domain.name in stage.on_signal:
                transition = stage.on_signal[domain.name]
            elif "default" in stage.on_signal:
                transition = stage.on_signal["default"]
            else:
                raise PipelineError(f"No default in stage '{stage.name}'")

            # Transition
            if transition.to is None:
                total = int(time.monotonic() - pipeline_start)
                summary = domain.content if domain else "complete"
                is_failure = domain and domain.name == "failed"
                if is_failure:
                    self.display.error(f"Pipeline stopped: {summary}")
                else:
                    self.display.done(summary, f"{round_num} rounds, {self._fmt_duration(total)}")
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
                self._live_signals = []
                result = executor.run(
                    prompt, model=runner.model, known_signals=known,
                    on_output=self._on_output,
                    on_signal=self._on_signal,
                )
                if result.exit_code == 0:
                    return result

                tag = f"{runner.executor}/{runner.model}" if runner.model else runner.executor
                self.display.warn(
                    f"{tag} failed "
                    f"(attempt {attempt}/2, exit {result.exit_code})"
                )
                if result.error:
                    self.display.warn(f"stderr: {result.error}")
                if attempt < 2:
                    self._wait()

            # Switch to fallback
            if label == "primary" and stage.fallback_runner:
                fb = stage.fallback_runner
                fb_tag = f"{fb.executor}/{fb.model}" if fb.model else fb.executor
                self.display.fallback(tag, fb_tag)

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

    def _on_output(self, text: str) -> None:
        """Real-time callback from executors — log streamed output."""
        self.display.executor_output(text)

    def _on_signal(self, sig) -> None:
        """Real-time callback from executors — display and collect signals."""
        self._live_signals.append(sig)
        if sig.name == "var" and "key" in sig.attrs:
            write_var(self.vars_path, sig.attrs["key"], sig.content)
            key = rich_escape(sig.attrs["key"])
            val = rich_escape(sig.content)
            self.display.info(f"[dim]var[/] {key}[dim]=[/]{val}")
        elif sig.name == "update":
            self.display.update(rich_escape(sig.content))
        else:
            self.display.domain_signal(sig.name, rich_escape(sig.content))

    def _run_step(self, label: str, raw_command: str) -> bool:
        """Run a shell command (pre_step / post_step). Returns True on success."""
        try:
            command = resolve_templates(raw_command, self.config_dir, self.vars_path)
        except TemplateError as e:
            self.display.warn(f"{label} template error: {e}")
            return False

        self.display.info(f"[dim]{label}[/]")
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.config_dir,
            capture_output=True,
            text=True,
        )

        if proc.stdout:
            for line in proc.stdout.strip().splitlines():
                self.display.executor_output(line)
        if proc.returncode != 0:
            if proc.stderr:
                self.display.warn(f"{label} stderr: {proc.stderr.strip()}")
            return False
        return True

    def _wait(self) -> None:
        self.cancel.wait(timeout=self.delay)
