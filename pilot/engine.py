"""Pipeline engine — core orchestration loop."""

from __future__ import annotations

import glob
import json
import os
import shutil
import threading

from pilot.executors import ExecutorPool
from pilot.models import (
    AgentStep,
    GateStep,
    LoopStep,
    PilotConfig,
    QAPair,
    RuntimeContext,
    ShellStep,
    Step,
)
from pilot.git import get_diff_command, get_head_hash
from pilot.progress import ProgressLog
from pilot.session import Session
from pilot.templates import expand_prompt, load_prompt


class PipelineError(Exception):
    pass


class SecurityError(Exception):
    pass


def _signal_summary(sig):
    """Format a signal for log output."""
    payload_preview = f" ({sig.payload[:80]})" if sig.payload else ""
    return f"  signal: {sig.type}{payload_preview}"


def _trunc(value: str, limit: int = 80) -> str:
    """Truncate a string for debug display. limit=0 means no truncation."""
    value = value.replace("\n", "\\n")
    if limit <= 0 or len(value) <= limit:
        return value
    return value[:limit] + f"…({len(value)})"


class PipelineEngine:
    def __init__(self, config: PilotConfig, runtime: RuntimeContext,
                 cancel_event: threading.Event | None = None):
        self.config = config
        self.runtime = runtime
        self.executors = ExecutorPool(error_patterns=config.error_patterns)
        self.progress = ProgressLog(runtime.progress_path)
        self.cancel_event = cancel_event or threading.Event()
        self.session = Session(runtime.session_dir)
        self._emissions_dir = os.path.join(runtime.session_dir, "emissions")
        self._qa_dir = os.path.join(runtime.session_dir, "qa")
        self._load_emissions()
        self._load_qa()

    def _check_cancelled(self) -> None:
        """Raise PipelineError if cancellation has been requested."""
        if self.cancel_event.is_set():
            raise PipelineError("Pipeline cancelled")

    # ── Debug state dump ───────────────────────────────────

    def _debug_state(self, step: Step, loop_vars: dict | None = None) -> None:
        """Print all available state vars before executing a step."""
        if not self.runtime.debug:
            return

        rt = self.runtime
        log = self.progress.log

        # Step identity
        step_type = type(step).__name__.replace("Step", "").lower()
        log(f"  🔍 debug — {step.id} ({step_type})")

        # Prior history: completed steps + current
        history = self.session.completed
        if history:
            log(f"  │ history: [{', '.join(history)}]")
        if self.session.current:
            log(f"  │ current: {self.session.current}")

        # Runtime vars
        log(f"  │ round={rt.round}  branch={rt.default_branch}")
        log(f"  │ diff_cmd={_trunc(rt.diff_command, 60)}")

        # All template vars — flat list, same as prompt expansion sees them
        tvars: dict[str, str] = {}
        tvars.update(self.config.inputs)
        tvars.update({
            "default_branch": rt.default_branch,
            "diff": rt.diff_command,
            "round": str(rt.round),
        })
        if rt.emissions:
            for k, v in rt.emissions.items():
                tvars[f"emit.{k}"] = v
        if loop_vars:
            tvars.update(loop_vars)
        if rt.questions:
            tvars["questions"] = f"({len(rt.questions)} pairs)"

        limit = rt.debug_truncate
        for k, v in tvars.items():
            log(f"  │ {{{{{k}}}}} = {_trunc(v, limit)}")

        # Step-specific params
        if isinstance(step, AgentStep):
            tool = step.tool or self.config.defaults.tool
            model = step.model or self.config.defaults.model
            retry = step.retry if step.retry is not None else self.config.defaults.retry
            log(f"  │ agent: tool={tool} model={model} retry={retry} prompt={_trunc(step.prompt, 50)}")
        elif isinstance(step, ShellStep):
            log(f"  │ shell: {_trunc(step.command, 60)}")
        elif isinstance(step, LoopStep):
            if step.over:
                log(f"  │ loop: over={step.over} as={step.as_var} order={step.order}")
            elif step.until:
                log(f"  │ loop: until={step.until} max_rounds={step.max_rounds}")

    # ── Emissions persistence ──────────────────────────────

    def _load_emissions(self) -> None:
        """Load previously persisted emissions from .pilot/emissions/."""
        if not os.path.isdir(self._emissions_dir):
            return
        for filename in os.listdir(self._emissions_dir):
            if not filename.endswith(".md"):
                continue
            key = filename[:-3]  # strip .md
            filepath = os.path.join(self._emissions_dir, filename)
            with open(filepath) as f:
                self.runtime.emissions[key] = f.read()

    def _save_emission(self, key: str, payload: str) -> None:
        """Persist a single emission to .pilot/emissions/{key}.md."""
        os.makedirs(self._emissions_dir, exist_ok=True)
        filepath = os.path.join(self._emissions_dir, f"{key}.md")
        with open(filepath, "w") as f:
            f.write(payload)

    # ── Q&A persistence ──────────────────────────────────

    def _load_qa(self) -> None:
        """Load previously persisted Q&A from .pilot/qa/."""
        if not os.path.isdir(self._qa_dir):
            return
        for filename in sorted(os.listdir(self._qa_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self._qa_dir, filename)
            with open(filepath) as f:
                data = json.load(f)
            self.runtime.questions.append(
                QAPair(step_id=data["step_id"], question=data["question"], answer=data["answer"])
            )

    def _save_qa(self, qa: QAPair) -> None:
        """Persist a Q&A pair to .pilot/qa/{step_id}-{NNN}.json."""
        os.makedirs(self._qa_dir, exist_ok=True)
        # Count existing files for this step to generate index
        existing = [f for f in os.listdir(self._qa_dir)
                    if f.startswith(f"{qa.step_id}-") and f.endswith(".json")]
        index = len(existing) + 1
        filepath = os.path.join(self._qa_dir, f"{qa.step_id}-{index:03d}.json")
        with open(filepath, "w") as f:
            json.dump({"step_id": qa.step_id, "question": qa.question, "answer": qa.answer}, f, indent=2)
            f.write("\n")

    # ── Step tracking (via session.json) ─────────────────

    def _sleep(self, ms: int | None = None) -> None:
        """Sleep for the configured delay, returning immediately if cancelled."""
        delay_ms = ms if ms is not None else self.config.iteration_delay_ms
        if delay_ms <= 0:
            return
        self.cancel_event.wait(timeout=delay_ms / 1000.0)

    def run(self) -> None:
        """Execute the full pipeline, auto-skipping completed steps."""
        self.session.start()
        self.progress.log("Pipeline started")
        try:
            for step in self.config.pipeline:
                self._check_cancelled()
                if self.session.is_done(step.id):
                    self.progress.log(f"  skipping {step.id} (already done)")
                    continue
                self.progress.section(step.id)
                self.session.mark_current(step.id)
                self.run_step(step, loop_vars=None)
                self.session.mark_done(step.id)
            self.progress.section("done")
            self.progress.log("Pipeline complete")
        finally:
            self.progress.close()

    def resume_from(self, step_id: str) -> None:
        """Execute the pipeline starting from a specific step."""
        self.progress.log(f"Resuming from step '{step_id}'")
        found = False
        try:
            for step in self.config.pipeline:
                self._check_cancelled()
                if step.id == step_id:
                    found = True
                if not found:
                    self.progress.log(f"  skipping {step.id}")
                    continue
                self.progress.section(step.id)
                self.session.mark_current(step.id)
                self.run_step(step, loop_vars=None)
                self.session.mark_done(step.id)
            if not found:
                raise PipelineError(f"Step '{step_id}' not found in pipeline")
            self.progress.section("done")
            self.progress.log("Pipeline complete")
        finally:
            self.progress.close()

    def run_step(self, step: Step, loop_vars: dict | None):
        self._debug_state(step, loop_vars)
        if isinstance(step, GateStep):
            self.run_gate(step)
            return None
        elif isinstance(step, AgentStep):
            result = self.run_agent(step, loop_vars)
        elif isinstance(step, ShellStep):
            result = self.run_shell(step, loop_vars)
        elif isinstance(step, LoopStep):
            self.run_loop(step, loop_vars)
            return None
        else:
            return None

        # Universal signal processing — runs for every step that
        # returns a result (agent, shell).  Loop-specific signals
        # (skip, approve, reject) are handled by the loop callers
        # after this returns.
        if result is not None:
            self.handle_signals(result.signals, step.id)
        return result

    def run_agent(self, step: AgentStep, loop_vars: dict | None):
        """Execute an agent step with optional retry on failure."""
        max_retries = step.retry if step.retry is not None else self.config.defaults.retry
        result = self._execute_agent(step, loop_vars)

        attempt = 0
        while result.exit_code != 0 and attempt < max_retries:
            attempt += 1
            self.progress.log(f"  retry {attempt}/{max_retries} for '{step.id}'")
            self._sleep()
            result = self._execute_agent(step, loop_vars)

        return result

    def _execute_agent(self, step: AgentStep, loop_vars: dict | None):
        """Run a single agent execution (no retry)."""
        # 1. Load prompt (file or inline) — resolve relative to config dir
        raw_prompt = load_prompt(step.prompt, self.runtime.config_dir)

        # 2. Expand all template variables
        prompt = expand_prompt(raw_prompt, self.config, self.runtime, loop_vars)

        # 3. Resolve executor (step override → defaults)
        tool = step.tool or self.config.defaults.tool
        model = step.model or self.config.defaults.model
        args = step.args if step.args is not None else self.config.defaults.args
        executor = self.executors.get(tool, script=step.script)

        # 4. Execute
        self.progress.log(f"▸ {step.id} ({tool}/{model})")
        result = executor.run(prompt, model, args=args)

        # 5. Log signals
        for sig in result.signals:
            self.progress.log(_signal_summary(sig))

        # 6. Log
        if result.error:
            self.progress.log(f"  exit_code={result.exit_code} error={result.error}")
        else:
            self.progress.log(f"  exit_code={result.exit_code}")
        return result

    def run_shell(self, step: ShellStep, loop_vars: dict | None):
        # Expand template vars in the command itself
        command = expand_prompt(step.command, self.config, self.runtime, loop_vars)

        self.progress.log(f"▸ {step.id} (shell)")
        executor = self.executors.get("shell")
        result = executor.run(command)

        if result.exit_code != 0:
            raise PipelineError(f"Shell step '{step.id}' failed: {result.error}")

        self.progress.log(f"  exit_code={result.exit_code}")
        return result

    def run_gate(self, step: GateStep) -> None:
        """Pause pipeline for user approval."""
        self.progress.log(f"▸ {step.id} (gate) — waiting for user")
        response = input(f"\n⏸  Gate: {step.id}\n   Press Enter to continue, or 'q' to quit: ")
        if response.strip().lower() == "q":
            raise PipelineError(f"User aborted at gate '{step.id}'")
        self.progress.log("  approved by user")

    def run_loop(self, step: LoopStep, parent_vars: dict | None) -> None:
        if step.over:
            self._run_iterator_loop(step, parent_vars)
        elif step.until:
            self._run_convergence_loop(step, parent_vars)
        else:
            raise PipelineError(f"Loop '{step.id}' needs 'over' or 'until'")

    def _run_iterator_loop(self, step: LoopStep, parent_vars: dict | None) -> None:
        """Iterate over files in a folder.

        Child steps may be LoopSteps themselves (nested loops).
        Each child's run_step() call recurses into run_loop() if needed,
        passing merged loop_vars down so inner loops inherit outer vars.
        """
        folder_raw = expand_prompt(step.over, self.config, self.runtime, parent_vars)
        # Resolve relative paths against config_dir (.pilot/)
        if not os.path.isabs(folder_raw):
            folder = os.path.join(self.runtime.config_dir, folder_raw)
        else:
            folder = folder_raw
        files = sorted(glob.glob(os.path.join(folder, "*.md")))

        if step.order == "desc":
            files = list(reversed(files))

        self.progress.log(f"▸ {step.id} (loop) — {len(files)} items")

        for i, filepath in enumerate(files, 1):
            self._check_cancelled()
            if i > 1:
                self._sleep()
            with open(filepath) as f:
                task_content = f.read()
            # Merge parent vars + this loop's var
            loop_vars = {**(parent_vars or {}), step.as_var: task_content}

            self.progress.log(f"  [{i}/{len(files)}] {os.path.basename(filepath)}")

            skipped = False
            for child in step.steps:
                result = self.run_step(child, loop_vars)
                # skip is the only iterator-specific signal; everything
                # else (emit, blocked, completed, etc.) is already
                # handled by handle_signals() in run_step().
                if result is not None and any(s.type == "skip" for s in result.signals):
                    self.progress.log(f"  ⤳ skipping {os.path.basename(filepath)}")
                    skipped = True
                    break

            if skipped:
                continue

            # Move completed task file
            completed_dir = os.path.join(folder, "completed")
            os.makedirs(completed_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(completed_dir, os.path.basename(filepath)))

    def _run_convergence_loop(self, step: LoopStep, parent_vars: dict | None) -> None:
        """Repeat steps until APPROVE signal or max_rounds.

        Can be nested inside an iterator loop — parent_vars carries
        the outer loop's variables (e.g., {{TASK}}) into this loop.
        """
        feedback = None
        original_diff = self.runtime.diff_command
        original_round = self.runtime.round

        try:
            for round_num in range(1, step.max_rounds + 1):
                self._check_cancelled()
                if round_num > 1:
                    self._sleep()
                self.runtime.round = round_num

                self.runtime.diff_command = get_diff_command(
                    self.runtime.default_branch, is_first=(round_num == 1),
                )

                loop_vars = {**(parent_vars or {})}
                if feedback:
                    loop_vars["FEEDBACK"] = feedback

                self.progress.log(f"  round {round_num}/{step.max_rounds}")

                head_before = get_head_hash()
                saw_reject = False

                for child in step.steps:
                    result = self.run_step(child, loop_vars)

                    if result is None:
                        continue

                    # approve and reject are the only convergence-specific
                    # signals; everything else (blocked, emit, completed,
                    # etc.) is already handled by handle_signals() in
                    # run_step().

                    # APPROVE → exit loop
                    if any(s.type == "approve" for s in result.signals):
                        self.progress.log(f"  ✓ approved at round {round_num}")
                        return

                    # REJECT → carry feedback to next round
                    rejects = [s for s in result.signals if s.type == "reject"]
                    if rejects:
                        feedback = rejects[-1].payload
                        loop_vars["FEEDBACK"] = feedback or ""
                        saw_reject = True

                head_after = get_head_hash()
                if not saw_reject and head_before and head_before == head_after:
                    self.progress.log(
                        f"  ✓ converged at round {round_num} (no new commits)"
                    )
                    return

            raise PipelineError(
                f"Convergence loop '{step.id}' reached max rounds ({step.max_rounds}) without approval"
            )
        finally:
            self.runtime.diff_command = original_diff
            self.runtime.round = original_round

    def handle_signals(self, signals: list, step_id: str) -> None:
        """Process universal signals (called from run_step for every result)."""
        for sig in signals:
            if sig.type == "blocked":
                raise PipelineError(f"Blocked in '{step_id}': {sig.payload}")

            elif sig.type == "question":
                try:
                    question = json.loads(sig.payload)
                    display = question.get("question", sig.payload)
                except (json.JSONDecodeError, TypeError):
                    question = None
                    display = sig.payload
                answer = input(f"\n❓ {display}\n> ")
                self.progress.log(f"  Q: {display}")
                self.progress.log(f"  A: {answer}")
                qa = QAPair(step_id=step_id, question=display, answer=answer)
                self.runtime.questions.append(qa)
                self._save_qa(qa)

            elif sig.type == "update":
                resolved = os.path.normpath(sig.path)
                if not resolved.startswith(".pilot" + os.sep) and resolved != ".pilot":
                    raise SecurityError(f"Update path escapes .pilot/: {sig.path}")
                os.makedirs(os.path.dirname(resolved), exist_ok=True)
                with open(resolved, "w") as f:
                    f.write(sig.payload)
                self.progress.log(f"  wrote {resolved}")

            elif sig.type == "draft":
                print(f"\n📄 Draft: {sig.label}\n")
                preview = sig.payload[:500] + "..." if len(sig.payload) > 500 else sig.payload
                print(preview)
                response = input("\n   Approve? (y/n): ")
                if response.strip().lower() == "y":
                    path = os.path.normpath(f".pilot/{sig.label}.md")
                    if not path.startswith(".pilot" + os.sep):
                        raise SecurityError(f"Draft label escapes .pilot/: {sig.label}")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(sig.payload)
                    self.progress.log(f"  draft '{sig.label}' approved, wrote {path}")

            elif sig.type == "completed":
                summary = f" ({sig.payload})" if sig.payload else ""
                self.progress.log(f"  ✓ task completed{summary}")

            elif sig.type == "emit":
                self.runtime.emissions[sig.key] = sig.payload
                self._save_emission(sig.key, sig.payload)
                self.progress.log(f"  emit: {sig.key}={sig.payload[:80]}")

            # skip and approve/reject are handled by loop callers;
            # ignored here (no warning needed).
