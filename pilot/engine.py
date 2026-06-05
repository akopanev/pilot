"""Pipeline engine — config-driven state machine loop."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pilot.display import Display
from pilot.executors import ExecutorPool
from pilot.executors.result import ExecutorResult
from pilot.models import PipelineConfig, PipelineState, Runner, Stage
from rich.markup import escape as rich_escape

from pilot.signals import BUILTIN_SIGNALS, Signal, parse_signals
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
        delay: float = 2.0,
        log_dir: str | None = None,
        cli_vars: dict[str, str] | None = None,
    ):
        self.config = config
        self.config_dir = config_dir
        self.state_path = state_path
        self.vars_path = vars_path
        self.display = display
        self.delay = delay
        self.log_dir = log_dir
        self.cli_vars = cli_vars or {}
        self.executors = ExecutorPool()
        self._live_signals: list[Signal] = []

        # Resume or start fresh
        saved = read_state(state_path)
        if saved and saved.stage in config.stages:
            self.state = saved
            self.display.info(
                f"[dim]Resuming[/] [stage]{saved.stage}[/]"
            )
        else:
            self.state = PipelineState(stage=config.start_stage)

    def _load_env_file(self) -> None:
        """Load .env file from config directory if it exists."""
        env_path = os.path.join(self.config_dir, ".env")
        if not os.path.isfile(env_path):
            return
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
        self.display.info("[dim].env loaded[/]")

    def _sync_env(self) -> None:
        """Export vars to file and os.environ.

        Writes config vars as defaults (won't overwrite agent-set values),
        then loads everything into os.environ.
        """
        from pilot.vars import read_vars

        existing = read_vars(self.vars_path)
        for key, value in self.config.vars.items():
            if key not in existing:
                write_var(self.vars_path, key, value)

        export_vars(self.vars_path)

    def _apply_var(self, key: str, value: str) -> None:
        """Persist a var to disk and into os.environ in one atomic step.

        Used for both agent-emitted <signal:var> tags and shell-step
        signal-scanning so vars become live for downstream consumers in
        the same round.
        """
        write_var(self.vars_path, key, value)
        os.environ[key] = value

    def _handle_var_signal(self, sig: Signal, source: str | None = None) -> bool:
        """If `sig` is a `<signal:var key=K>V</signal:var>` tag, persist it
        and emit a display line. Returns True iff the signal was a var.

        Centralises the var-handling logic shared by `_on_signal` (executor
        callbacks) and `_run_step` (shell-hook stdout scanning).
        """
        if sig.name != "var" or "key" not in sig.attrs:
            return False
        self._apply_var(sig.attrs["key"], sig.content)
        key = rich_escape(sig.attrs["key"])
        val = rich_escape(sig.content)
        prefix = f"\\[{source}] " if source else ""
        self.display.info(f"{prefix}[dim]var[/] {key}[dim]=[/]{val}")
        return True

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        if seconds >= 3600:
            return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"
        if seconds >= 60:
            return f"{seconds // 60}m{seconds % 60:02d}s"
        return f"{seconds}s"

    def run(self) -> None:
        # Export config dir so scripts and prompts can reference it
        abs_config_dir = os.path.abspath(self.config_dir)
        os.environ["PILOT_CONFIG_DIR"] = abs_config_dir
        os.environ["PILOT_PIPELINE_NAME"] = os.path.basename(abs_config_dir)
        write_var(self.vars_path, "PILOT_CONFIG_DIR", abs_config_dir)

        # Load .env (secrets) before anything
        self._load_env_file()

        # CLI vars: applied before _sync_env so they take precedence over
        # pipeline-yaml `vars:` defaults (which _sync_env writes only when
        # absent). They remain mutable by pre_step / agent signals at runtime.
        for key, value in self.cli_vars.items():
            self._apply_var(key, value)

        # Sync config vars so pre_pipeline can use them
        self._sync_env()

        # Pipeline pre_pipeline
        if self.config.pre_pipeline:
            if not self._run_step("pre_pipeline", self.config.pre_pipeline, show_output=True):
                raise PipelineError("pre_pipeline failed")

        self._pipeline_rounds = 0
        self._pipeline_last_stage = self.state.stage
        pipeline_start = time.monotonic()

        exit_status = "failed"
        try:
            exit_status = self._main_loop()
        finally:
            # Expose pipeline metadata as env vars for hooks
            total = int(time.monotonic() - pipeline_start)
            os.environ["PILOT_EXIT_STATUS"] = exit_status
            os.environ["PILOT_DURATION"] = self._fmt_duration(total)
            os.environ["PILOT_ROUNDS"] = str(self._pipeline_rounds)
            os.environ["PILOT_LAST_STAGE"] = self._pipeline_last_stage

            # Clear state before conditional hooks (avoid stale state if chaining)
            if exit_status == "success":
                clear_state(self.state_path)
                clear_vars(self.vars_path)

            # Conditional hooks (notify / chain / cleanup)
            if exit_status == "success" and self.config.on_pipeline_success:
                if not self._run_step("on_pipeline_success", self.config.on_pipeline_success, show_output=True):
                    self.display.warn("on_pipeline_success failed")
            elif exit_status == "failed" and self.config.on_pipeline_failure:
                if not self._run_step("on_pipeline_failure", self.config.on_pipeline_failure, show_output=True):
                    self.display.warn("on_pipeline_failure failed")

    def _main_loop(self) -> str:
        """Run the main pipeline loop. Returns 'success' or 'failed'."""
        consecutive_failures = 0
        round_num = 0
        pipeline_start = time.monotonic()

        while True:
            round_num += 1
            round_start = time.monotonic()
            self._sync_env()

            stage = self.config.stages.get(self.state.stage)
            if not stage:
                raise PipelineError(f"Unknown stage: {self.state.stage}")
            self._pipeline_rounds = round_num
            self._pipeline_last_stage = stage.name

            if stage.is_ensemble:
                runners_info = [(r.executor, r.model) for r in stage.runners]
                self.display.round_header_ensemble(round_num, stage.name, runners_info)
            else:
                self.display.round_header(
                    round_num,
                    stage.name,
                    stage.runner.executor,
                    stage.runner.model,
                )

            # pre_step — shell command before main executor; may emit
            # <signal:var> tags that become live for the executor below.
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

            # Per-runner stages defer template resolution until each worker
            # spawns, so runner.vars overrides apply correctly.
            raw_prompt = self._get_raw_prompt(stage)

            # Known signals for this stage. Ensemble stages capture every
            # signal name (informational tags like <signal:done verdict=...>
            # belong on disk even though routing always falls through to
            # 'default').
            if stage.is_ensemble:
                known = None
            else:
                known = set(stage.on_signal.keys()) | BUILTIN_SIGNALS

            # Run executor(s)
            self._live_signals = []
            if stage.is_ensemble:
                result = self._run_ensemble(stage, raw_prompt, known, round_num)
            else:
                result = self._run_with_retries(stage, raw_prompt, known)

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
                if result.error:
                    self.display.warn(result.error)
                if consecutive_failures >= 3:
                    raise PipelineError("3 consecutive round failures")
                self._wait()
                continue

            consecutive_failures = 0

            # Signals already displayed in real-time via _on_signal callback
            signals = self._live_signals

            # Find first domain signal for routing (ensemble stages route via 'default' only)
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

            # Transition — exit pipeline
            if transition.to is None:
                total = int(time.monotonic() - pipeline_start)
                summary = domain.content if domain else "complete"
                if transition.fail:
                    self.display.error(f"Pipeline stopped: {summary}")
                    return "failed"
                else:
                    self.display.done(summary, f"{round_num} rounds, {self._fmt_duration(total)}")
                    return "success"

            # Transition — next stage
            old_stage = self.state.stage
            self.state.stage = transition.to
            write_state(self.state_path, self.state)
            self.display.transition(old_stage, transition.to)
            self._wait()

        return "failed"  # unreachable, loop exits via return or exception

    def _make_callbacks(self, source: str | None):
        """Build (on_output, on_signal) closures.

        source: per-runner tag for ensemble stages (e.g. "claude-code/opus"),
                None for single-runner stages.
        """
        def on_output(text: str) -> None:
            self.display.executor_output(text, source=source)

        def on_signal(sig: Signal) -> None:
            if source:
                sig.attrs = {**sig.attrs, "source": source}
            self._on_signal(sig)

        return on_output, on_signal

    def _resolve_runner_vars(self, runner: Runner) -> dict[str, str]:
        """Resolve each runner.vars value as a template against global vars.

        This lets ensemble runners reference pre_step-emitted vars
        (`{{var:ROUND_DIR}}`) inside their per-runner config without any
        new template namespace.
        """
        if not runner.vars:
            return {}
        resolved: dict[str, str] = {}
        for k, v in runner.vars.items():
            resolved[k] = resolve_templates(v, self.config_dir, self.vars_path)
        return resolved

    def _resolve_prompt(self, raw: str, runner: Runner) -> str:
        """Resolve a raw prompt with runner.vars merged as overrides."""
        return resolve_templates(
            raw, self.config_dir, self.vars_path,
            vars_overrides=self._resolve_runner_vars(runner) or None,
        )

    def _run_with_retries(self, stage: Stage, raw_prompt: str,
                          known: set[str] | None) -> ExecutorResult:
        """Try primary runner twice, then fallback runner twice.

        Returns the first successful result, or the last failed result.
        """
        runners = [(stage.runner, "primary")]
        if stage.fallback_runner:
            runners.append((stage.fallback_runner, "fallback"))

        on_output, on_signal = self._make_callbacks(None)

        result: ExecutorResult | None = None
        for runner, label in runners:
            try:
                prompt = self._resolve_prompt(raw_prompt, runner)
            except TemplateError as e:
                raise PipelineError(f"Template error: {e}") from e

            executor = self.executors.get(runner.executor)
            for attempt in range(1, 3):
                # Reset live signals on retry — only keep the final attempt's signals
                self._live_signals = []
                result = executor.run(
                    prompt, model=runner.model, known_signals=known,
                    on_output=on_output,
                    on_signal=on_signal,
                    args=runner.args,
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

    def _run_ensemble(self, stage: Stage, raw_prompt: str,
                      known: set[str] | None,
                      round_num: int) -> ExecutorResult:
        """Run all runners on the same prompt and write per-runner internal logs.

        Each worker resolves the prompt with its own runner.vars overrides.
        Where the model writes its formatted artifact is entirely the
        pipeline author's choice (declared via `runner.vars` and
        referenced inside the prompt as `{{var:NAME}}`).

        The engine still keeps an internal log of each runner's stdout +
        parsed signals under <log_dir>/round-NNN-<stage>/ for debugging,
        but does not expose that path to the pipeline.
        """
        log_round_dir: str | None = None
        if self.log_dir:
            log_round_dir = os.path.join(
                self.log_dir, f"round-{round_num:03d}-{stage.name}"
            )
            os.makedirs(log_round_dir, exist_ok=True)

        runners = stage.runners
        timeout = stage.per_runner_timeout

        descriptors: list[tuple[Runner, str]] = []
        seen_slugs: set[str] = set()
        for r in runners:
            base = f"{r.executor}-{r.model}" if r.model else r.executor
            slug = base.replace("/", "-")
            if slug in seen_slugs:
                i = 2
                while f"{slug}-{i}" in seen_slugs:
                    i += 1
                slug = f"{slug}-{i}"
            seen_slugs.add(slug)
            descriptors.append((r, slug))

        results: dict[str, ExecutorResult] = {}

        def worker(runner: Runner, source: str) -> tuple[str, ExecutorResult]:
            on_output, on_signal = self._make_callbacks(source)
            try:
                worker_prompt = self._resolve_prompt(raw_prompt, runner)
            except TemplateError as e:
                self.display.warn(f"[{source}] template error: {e}")
                return source, ExecutorResult(
                    output="", exit_code=1, error=str(e), signals=[],
                )

            executor = self.executors.get(runner.executor)
            cancel = threading.Event()
            timer: threading.Timer | None = None
            if timeout:
                timer = threading.Timer(float(timeout), cancel.set)
                timer.daemon = True
                timer.start()

            worker_start = time.monotonic()
            run_result: ExecutorResult | None = None
            try:
                for attempt in range(1, 3):
                    run_result = executor.run(
                        worker_prompt, model=runner.model, known_signals=known,
                        on_output=on_output, on_signal=on_signal,
                        cancel=cancel,
                        args=runner.args,
                    )
                    if run_result.exit_code == 0:
                        break
                    if cancel.is_set():
                        break
                    tag = (
                        f"{runner.executor}/{runner.model}"
                        if runner.model else runner.executor
                    )
                    self.display.warn(
                        f"[{source}] {tag} failed "
                        f"(attempt {attempt}/2, exit {run_result.exit_code})"
                    )
                    if attempt < 2:
                        time.sleep(self.delay)
            finally:
                if timer:
                    timer.cancel()

            # If the timer fired, mark as timeout — but only when we don't
            # already have a successful result. A clean exit_code 0 wins
            # over a late-firing cancel (race window during executor cleanup).
            if cancel.is_set() and (run_result is None or run_result.exit_code != 0):
                run_result = ExecutorResult(
                    output=run_result.output if run_result else "",
                    exit_code=124,
                    error=f"per_runner_timeout exceeded ({timeout}s)",
                    signals=run_result.signals if run_result else [],
                )

            # Internal debug logs only — NOT the user's artifact, which
            # the model writes to wherever runner.vars told it to.
            if log_round_dir:
                try:
                    with open(os.path.join(log_round_dir, f"{source}.txt"), "w") as f:
                        f.write(run_result.output or "")
                    with open(os.path.join(log_round_dir, f"{source}.signals.json"), "w") as f:
                        json.dump(
                            [
                                {"name": s.name, "content": s.content, "attrs": s.attrs}
                                for s in (run_result.signals or [])
                            ],
                            f,
                            indent=2,
                        )
                except OSError as e:
                    self.display.warn(f"[{source}] failed to write log: {e}")

            elapsed = int(time.monotonic() - worker_start)
            self.display.ensemble_runner_done(
                source,
                run_result.exit_code,
                elapsed,
                len(run_result.signals or []),
            )
            return source, run_result

        if stage.parallel and len(descriptors) > 1:
            with ThreadPoolExecutor(max_workers=len(descriptors)) as pool:
                futures = [pool.submit(worker, r, slug) for r, slug in descriptors]
                for fut in as_completed(futures):
                    src, res = fut.result()
                    results[src] = res
        else:
            for r, slug in descriptors:
                src, res = worker(r, slug)
                results[src] = res

        successes = sum(1 for r in results.values() if r.exit_code == 0)
        failures = len(runners) - successes

        threshold = stage.min_success or len(runners)
        round_ok = successes >= threshold

        return ExecutorResult(
            output="",
            exit_code=0 if round_ok else 1,
            error=(
                None if round_ok
                else f"{failures}/{len(runners)} runner(s) failed; "
                     f"need >= {threshold} success"
            ),
            signals=list(self._live_signals),
        )

    def _get_raw_prompt(self, stage: Stage) -> str:
        """Return the unresolved prompt (or shell command) for a stage.

        Resolution is deferred to per-runner time so runner.vars overrides
        compose correctly.
        """
        if stage.is_ensemble:
            return stage.prompt or ""
        if stage.runner is not None and stage.runner.executor == "shell":
            return stage.runner.command or ""
        return stage.prompt or ""

    def _on_signal(self, sig: Signal) -> None:
        """Real-time callback from executors — display and collect signals."""
        self._live_signals.append(sig)
        source = sig.attrs.get("source")
        if self._handle_var_signal(sig, source=source):
            return
        if sig.name == "update":
            self.display.update(rich_escape(sig.content), source=source)
        else:
            self.display.domain_signal(
                sig.name, rich_escape(sig.content), source=source,
            )

    def _run_step(self, label: str, raw_command: str,
                  show_output: bool = False) -> bool:
        """Run a shell command. Returns True on success.

        Stdout is scanned for `<signal:var key=NAME>VALUE</signal:var>`
        tags so pre/post hooks can publish vars using the same protocol
        agents use. Vars are applied to both the vars file and os.environ
        immediately so the same round's executor can see them.

        show_output: True for pipeline hooks (always visible),
                     False for stage pre/post steps (verbose only).
        """
        try:
            command = resolve_templates(raw_command, self.config_dir, self.vars_path)
        except TemplateError as e:
            self.display.warn(f"{label} template error: {e}")
            return False

        self.display.info(f"[dim]{label}[/]")
        proc = subprocess.run(
            command,
            shell=True,
            executable="bash",
            cwd=self.config_dir,
            capture_output=True,
            text=True,
        )

        if proc.stdout:
            for sig in parse_signals(proc.stdout):
                self._handle_var_signal(sig)

            for line in proc.stdout.strip().splitlines():
                if show_output:
                    self.display.info(f"  [dim]{line}[/]")
                else:
                    self.display.executor_output(line)
        if proc.returncode != 0:
            if proc.stderr:
                self.display.warn(f"{label} stderr: {proc.stderr.strip()}")
            return False
        return True

    def _wait(self) -> None:
        time.sleep(self.delay)
