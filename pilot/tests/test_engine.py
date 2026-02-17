"""Tests for pipeline engine."""

import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

from pilot.engine import PipelineEngine, PipelineError
from pilot.executors.claude import ExecutorResult
from pilot.models import (
    AgentDefaults,
    AgentStep,
    GateStep,
    LoopStep,
    PilotConfig,
    QAPair,
    RuntimeContext,
    ShellStep,
)
from pilot.signals import Signal

import json

import pytest


def _make_engine(steps, tmpdir, cancel_event=None, defaults=None):
    config = PilotConfig(
        version="1.0",
        inputs={},
        defaults=defaults or AgentDefaults(),
        pipeline=steps,
    )
    session_dir = os.path.join(tmpdir, "session")
    os.makedirs(session_dir, exist_ok=True)
    progress_path = os.path.join(session_dir, "progress.log")
    runtime = RuntimeContext(
        project_dir=tmpdir,
        config_dir=tmpdir,
        session_dir=session_dir,
        default_branch="main",
        progress_path=progress_path,
        diff_command="git diff main...HEAD",
    )
    return PipelineEngine(config, runtime, cancel_event=cancel_event)


def test_shell_step_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        step = ShellStep(id="test-shell", command="echo hello")
        engine = _make_engine([step], tmpdir)
        result = engine.run_shell(step, None)
        assert result.exit_code == 0
        assert "hello" in result.output


def test_shell_step_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        step = ShellStep(id="fail-shell", command="exit 1")
        engine = _make_engine([step], tmpdir)
        with pytest.raises(PipelineError, match="fail-shell"):
            engine.run_shell(step, None)


def test_shell_step_template_expansion():
    with tempfile.TemporaryDirectory() as tmpdir:
        step = ShellStep(id="echo-branch", command="echo {{default_branch}}")
        engine = _make_engine([step], tmpdir)
        result = engine.run_shell(step, None)
        assert "main" in result.output


@patch("builtins.input", return_value="")
def test_gate_continues(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        step = GateStep(id="gate1")
        engine = _make_engine([step], tmpdir)
        engine.run_gate(step)  # should not raise


@patch("builtins.input", return_value="q")
def test_gate_aborts(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        step = GateStep(id="gate1")
        engine = _make_engine([step], tmpdir)
        with pytest.raises(PipelineError, match="aborted"):
            engine.run_gate(step)


def test_resume_skips_steps():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
            ShellStep(id="step3", command="echo 3"),
        ]
        engine = _make_engine(steps, tmpdir)
        # Capture which steps get executed
        executed = []
        original_run_shell = engine.run_shell

        def tracking_run_shell(step, loop_vars):
            executed.append(step.id)
            return original_run_shell(step, loop_vars)

        engine.run_shell = tracking_run_shell
        engine.resume_from("step2")
        assert "step1" not in executed
        assert "step2" in executed
        assert "step3" in executed


# ── Change 4: Cancel event ─────────────────────────────────

def test_cancel_event_stops_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
        ]
        cancel_event = threading.Event()
        cancel_event.set()  # Pre-set = immediately cancelled
        engine = _make_engine(steps, tmpdir, cancel_event=cancel_event)
        with pytest.raises(PipelineError, match="cancelled"):
            engine.run()


# ── Change 2: Retry logic ──────────────────────────────────

def test_retry_on_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a prompt file
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        step = AgentStep(id="flaky", prompt="task.md", retry=2)
        defaults = AgentDefaults(retry=0)
        engine = _make_engine([step], tmpdir, defaults=defaults)
        engine.config.iteration_delay_ms = 0  # no delay in tests

        # Track _execute_agent calls
        call_count = 0
        original_execute = engine._execute_agent

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            # Fail on first two calls, succeed on third
            result = ExecutorResult(
                output="output",
                exit_code=1 if call_count < 3 else 0,
                error="fail" if call_count < 3 else None,
            )
            return result

        engine._execute_agent = mock_execute
        result = engine.run_agent(step, None)
        assert call_count == 3  # initial + 2 retries
        assert result.exit_code == 0


# ── Iterator loop ──────────────────────────────────────────

def test_iterator_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create task files
        tasks_dir = os.path.join(tmpdir, "tasks")
        os.makedirs(tasks_dir)
        for name in ["001.md", "002.md"]:
            with open(os.path.join(tasks_dir, name), "w") as f:
                f.write(f"content of {name}")

        # Use absolute path so expand_prompt resolves correctly
        loop_step = LoopStep(
            id="dev",
            steps=[ShellStep(id="echo-task", command="echo ok")],
            over=tasks_dir,
            as_var="TASK",
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        executed = []
        original_run_shell = engine.run_shell

        def tracking_run_shell(step, loop_vars):
            executed.append(step.id)
            assert "TASK" in loop_vars
            return original_run_shell(step, loop_vars)

        engine.run_shell = tracking_run_shell
        engine._run_iterator_loop(loop_step, None)

        assert len(executed) == 2
        # Files should be moved to completed/
        assert os.path.isdir(os.path.join(tasks_dir, "completed"))
        assert len(os.listdir(os.path.join(tasks_dir, "completed"))) == 2


# ── Convergence loop ──────────────────────────────────────

def test_convergence_loop_approve():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a prompt file
        prompt_file = os.path.join(tmpdir, "review.md")
        with open(prompt_file, "w") as f:
            f.write("review this")

        loop_step = LoopStep(
            id="review-loop",
            steps=[AgentStep(id="review", prompt="review.md")],
            until="APPROVE",
            max_rounds=5,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        from pilot.signals import Signal

        call_count = 0

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            # Reject first, approve second
            if call_count == 1:
                signals = [Signal(type="reject", payload="needs work")]
            else:
                signals = [Signal(type="approve")]
            return ExecutorResult(output="out", exit_code=0, error=None, signals=signals)

        engine._execute_agent = mock_execute

        # get_head_hash called twice per round (before + after)
        # Round 1: before=aaa, after=bbb (different → no fallback, reject → continue)
        # Round 2: approve fires before head check
        heads = iter(["aaa", "bbb", "ccc", "ddd"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, None)

        assert call_count == 2  # rejected once, approved second


def test_convergence_loop_max_rounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        loop_step = LoopStep(
            id="loop",
            steps=[AgentStep(id="agent", prompt="task.md")],
            until="APPROVE",
            max_rounds=2,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        def mock_execute(step, loop_vars):
            return ExecutorResult(output="out", exit_code=0, error=None, signals=[])

        engine._execute_agent = mock_execute

        # get_head_hash called 2x per round: before + after
        # Need different values each call so no-commit fallback doesn't trigger
        heads = iter(["aaa", "bbb", "ccc", "ddd"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            with pytest.raises(PipelineError, match="reached max rounds"):
                engine._run_convergence_loop(loop_step, None)


# ── Completed signal ──────────────────────────────────────

def test_completed_logged_outside_loops():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="completed", payload="all done")]
        engine.handle_signals(signals, "setup")

        with open(engine.progress.path) as f:
            log_content = f.read()
        assert "task completed" in log_content
        assert "all done" in log_content


def test_completed_does_not_exit_convergence_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        loop_step = LoopStep(
            id="loop",
            steps=[AgentStep(id="agent", prompt="task.md")],
            until="APPROVE",
            max_rounds=3,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        call_count = 0

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Emit completed but NOT approve — loop should continue
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="completed", payload="step done")],
                )
            else:
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="approve")],
                )

        engine._execute_agent = mock_execute

        heads = iter(["a", "b", "c", "d", "e", "f"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, None)

        assert call_count == 3  # completed didn't exit early


def test_reject_feedback_injected_same_round_for_fix_step():
    with tempfile.TemporaryDirectory() as tmpdir:
        review_prompt = os.path.join(tmpdir, "review.md")
        fix_prompt = os.path.join(tmpdir, "fix.md")
        with open(review_prompt, "w") as f:
            f.write("review")
        with open(fix_prompt, "w") as f:
            f.write("fix {{FEEDBACK}}")

        loop_step = LoopStep(
            id="review-fix",
            steps=[
                AgentStep(id="review", prompt="review.md"),
                AgentStep(id="fix", prompt="fix.md"),
            ],
            until="APPROVE",
            max_rounds=2,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        seen_fix_prompts = []

        def mock_run(prompt, model, args=None):
            if prompt == "review":
                return ExecutorResult(
                    output="<pilot:reject>missing tests</pilot:reject>",
                    exit_code=0,
                    error=None,
                    signals=[Signal(type="reject", payload="missing tests")],
                )
            seen_fix_prompts.append(prompt)
            return ExecutorResult(
                output="<pilot:approve/>",
                exit_code=0,
                error=None,
                signals=[Signal(type="approve")],
            )

        executor = engine.executors.get("claude-code")
        executor.run = mock_run

        heads = iter(["a", "b", "c", "d"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, {"TASK": "do work"})

        assert seen_fix_prompts
        assert "missing tests" in seen_fix_prompts[0]


# ── Skip signal ───────────────────────────────────────────

def test_skip_in_iterator_loop_file_stays():
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_dir = os.path.join(tmpdir, "tasks")
        os.makedirs(tasks_dir)
        for name in ["001.md", "002.md", "003.md"]:
            with open(os.path.join(tasks_dir, name), "w") as f:
                f.write(f"content of {name}")

        loop_step = LoopStep(
            id="dev",
            steps=[AgentStep(id="impl", prompt="task.md")],
            over=tasks_dir,
            as_var="TASK",
        )

        # Create prompt file
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        call_count = 0

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            # Skip the second file (002.md)
            if "002" in loop_vars.get("TASK", ""):
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="skip", payload="not applicable")],
                )
            return ExecutorResult(output="out", exit_code=0, error=None, signals=[])

        engine._execute_agent = mock_execute
        engine._run_iterator_loop(loop_step, None)

        assert call_count == 3
        # 002.md should still be in tasks_dir (not moved to completed/)
        assert os.path.exists(os.path.join(tasks_dir, "002.md"))
        # 001.md and 003.md should be in completed/
        completed_dir = os.path.join(tasks_dir, "completed")
        completed_files = os.listdir(completed_dir)
        assert "001.md" in completed_files
        assert "003.md" in completed_files
        assert "002.md" not in completed_files


def test_skip_breaks_out_of_child_steps():
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_dir = os.path.join(tmpdir, "tasks")
        os.makedirs(tasks_dir)
        with open(os.path.join(tasks_dir, "001.md"), "w") as f:
            f.write("task content")

        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        # Two child steps — skip in first should prevent second from running
        loop_step = LoopStep(
            id="dev",
            steps=[
                AgentStep(id="check", prompt="task.md"),
                AgentStep(id="impl", prompt="task.md"),
            ],
            over=tasks_dir,
            as_var="TASK",
        )

        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        executed_steps = []

        def mock_execute(step, loop_vars):
            executed_steps.append(step.id)
            if step.id == "check":
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="skip")],
                )
            return ExecutorResult(output="out", exit_code=0, error=None, signals=[])

        engine._execute_agent = mock_execute
        engine._run_iterator_loop(loop_step, None)

        assert "check" in executed_steps
        assert "impl" not in executed_steps  # skip broke out before impl ran


# ── Emit signal ───────────────────────────────────────────

def test_emit_stores_in_runtime():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="emit", key="api_url", payload="https://api.com")]
        engine.handle_signals(signals, "setup")

        assert engine.runtime.emissions["api_url"] == "https://api.com"


def test_emit_last_wins_on_duplicate_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [
            Signal(type="emit", key="val", payload="first"),
            Signal(type="emit", key="val", payload="second"),
        ]
        engine.handle_signals(signals, "setup")

        assert engine.runtime.emissions["val"] == "second"


def test_emit_persists_across_convergence_rounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        loop_step = LoopStep(
            id="loop",
            steps=[AgentStep(id="agent", prompt="task.md")],
            until="APPROVE",
            max_rounds=3,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        call_count = 0

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="emit", key="round1_val", payload="from_round1")],
                )
            else:
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="approve")],
                )

        engine._execute_agent = mock_execute

        heads = iter(["a", "b", "c", "d"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, None)

        # Emission from round 1 should still be present
        assert engine.runtime.emissions["round1_val"] == "from_round1"


def test_emit_in_iterator_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_dir = os.path.join(tmpdir, "tasks")
        os.makedirs(tasks_dir)
        with open(os.path.join(tasks_dir, "001.md"), "w") as f:
            f.write("task content")

        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        loop_step = LoopStep(
            id="dev",
            steps=[AgentStep(id="impl", prompt="task.md")],
            over=tasks_dir,
            as_var="TASK",
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        def mock_execute(step, loop_vars):
            return ExecutorResult(
                output="out", exit_code=0, error=None,
                signals=[Signal(type="emit", key="result", payload="done")],
            )

        engine._execute_agent = mock_execute
        engine._run_iterator_loop(loop_step, None)

        assert engine.runtime.emissions["result"] == "done"


# ── Question signal fix ───────────────────────────────────

@patch("builtins.input", return_value="plain answer")
def test_question_with_plain_text(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="question", payload="What database should I use?")]
        # Should not crash — plain text payload (not JSON)
        engine.handle_signals(signals, "ask")

        with open(engine.progress.path) as f:
            log_content = f.read()
        assert "What database should I use?" in log_content


@patch("builtins.input", return_value="json answer")
def test_question_with_json_still_works(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="question", payload='{"question": "Which DB?"}')]
        engine.handle_signals(signals, "ask")

        with open(engine.progress.path) as f:
            log_content = f.read()
        assert "Which DB?" in log_content


# ── Edge case: skip takes precedence over completed ───────

# ── Args passed through to executor ──────────────────────

def test_args_passed_to_executor():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        step = AgentStep(id="task", prompt="task.md", args=["--sandbox", "read-only"])
        engine = _make_engine([step], tmpdir)

        captured_args = {}

        def mock_run(prompt, model, args=None):
            captured_args["args"] = args
            return ExecutorResult(output="ok", exit_code=0, error=None)

        # Patch the executor's run method
        executor = engine.executors.get("claude-code")
        executor.run = mock_run
        engine._execute_agent(step, None)

        assert captured_args["args"] == ["--sandbox", "read-only"]


def test_args_falls_back_to_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        step = AgentStep(id="task", prompt="task.md")  # args=None
        defaults = AgentDefaults(args=["--default-flag"])
        engine = _make_engine([step], tmpdir, defaults=defaults)

        captured_args = {}

        def mock_run(prompt, model, args=None):
            captured_args["args"] = args
            return ExecutorResult(output="ok", exit_code=0, error=None)

        executor = engine.executors.get("claude-code")
        executor.run = mock_run
        engine._execute_agent(step, None)

        assert captured_args["args"] == ["--default-flag"]


def test_args_step_overrides_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        step = AgentStep(id="task", prompt="task.md", args=["--step-flag"])
        defaults = AgentDefaults(args=["--default-flag"])
        engine = _make_engine([step], tmpdir, defaults=defaults)

        captured_args = {}

        def mock_run(prompt, model, args=None):
            captured_args["args"] = args
            return ExecutorResult(output="ok", exit_code=0, error=None)

        executor = engine.executors.get("claude-code")
        executor.run = mock_run
        engine._execute_agent(step, None)

        assert captured_args["args"] == ["--step-flag"]


def test_args_empty_list_overrides_defaults():
    """An explicit empty args list on a step should override defaults (not fall back)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        step = AgentStep(id="task", prompt="task.md", args=[])
        defaults = AgentDefaults(args=["--default-flag"])
        engine = _make_engine([step], tmpdir, defaults=defaults)

        captured_args = {}

        def mock_run(prompt, model, args=None):
            captured_args["args"] = args
            return ExecutorResult(output="ok", exit_code=0, error=None)

        executor = engine.executors.get("claude-code")
        executor.run = mock_run
        engine._execute_agent(step, None)

        assert captured_args["args"] == []


def test_skip_takes_precedence_over_completed_in_iterator():
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_dir = os.path.join(tmpdir, "tasks")
        os.makedirs(tasks_dir)
        with open(os.path.join(tasks_dir, "001.md"), "w") as f:
            f.write("task content")

        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do something")

        loop_step = LoopStep(
            id="dev",
            steps=[AgentStep(id="impl", prompt="task.md")],
            over=tasks_dir,
            as_var="TASK",
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        def mock_execute(step, loop_vars):
            return ExecutorResult(
                output="out", exit_code=0, error=None,
                signals=[
                    Signal(type="completed", payload="done"),
                    Signal(type="skip"),
                ],
            )

        engine._execute_agent = mock_execute
        engine._run_iterator_loop(loop_step, None)

        # File should NOT be moved to completed/ because skip takes precedence
        assert os.path.exists(os.path.join(tasks_dir, "001.md"))
        assert not os.path.exists(os.path.join(tasks_dir, "completed", "001.md"))


# ── Q&A persistence ──────────────────────────────────────

@patch("builtins.input", return_value="PostgreSQL")
def test_question_saves_qa_to_runtime(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="question", payload="Which DB?")]
        engine.handle_signals(signals, "prd")

        assert len(engine.runtime.questions) == 1
        qa = engine.runtime.questions[0]
        assert qa.step_id == "prd"
        assert qa.question == "Which DB?"
        assert qa.answer == "PostgreSQL"


@patch("builtins.input", return_value="Yes")
def test_question_persists_to_disk(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="question", payload="Monorepo?")]
        engine.handle_signals(signals, "plan")

        # Check file was written
        qa_dir = os.path.join(tmpdir, "session", "qa")
        assert os.path.isdir(qa_dir)
        files = os.listdir(qa_dir)
        assert len(files) == 1
        assert files[0] == "plan-001.json"

        with open(os.path.join(qa_dir, files[0])) as f:
            data = json.load(f)
        assert data["step_id"] == "plan"
        assert data["question"] == "Monorepo?"
        assert data["answer"] == "Yes"


def test_qa_loaded_on_engine_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pre-populate qa/ directory
        qa_dir = os.path.join(tmpdir, "session", "qa")
        os.makedirs(qa_dir)
        with open(os.path.join(qa_dir, "prd-001.json"), "w") as f:
            json.dump({"step_id": "prd", "question": "DB?", "answer": "Postgres"}, f)
        with open(os.path.join(qa_dir, "prd-002.json"), "w") as f:
            json.dump({"step_id": "prd", "question": "ORM?", "answer": "SQLAlchemy"}, f)

        engine = _make_engine([], tmpdir)

        assert len(engine.runtime.questions) == 2
        assert engine.runtime.questions[0].question == "DB?"
        assert engine.runtime.questions[1].question == "ORM?"


@patch("builtins.input", side_effect=["A1", "A2"])
def test_multiple_questions_incremental_numbering(mock_input):
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        engine.handle_signals([Signal(type="question", payload="Q1?")], "prd")
        engine.handle_signals([Signal(type="question", payload="Q2?")], "prd")

        qa_dir = os.path.join(tmpdir, "session", "qa")
        files = sorted(os.listdir(qa_dir))
        assert files == ["prd-001.json", "prd-002.json"]


# ── Feedback accumulation ─────────────────────────────

def test_feedback_accumulates_across_rounds():
    """Reject feedback from all rounds should be visible, not just the latest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        review_prompt = os.path.join(tmpdir, "review.md")
        fix_prompt = os.path.join(tmpdir, "fix.md")
        with open(review_prompt, "w") as f:
            f.write("review {{FEEDBACK}}")
        with open(fix_prompt, "w") as f:
            f.write("fix {{FEEDBACK}}")

        loop_step = LoopStep(
            id="review-fix",
            steps=[
                AgentStep(id="review", prompt="review.md"),
                AgentStep(id="fix", prompt="fix.md"),
            ],
            until="APPROVE",
            max_rounds=3,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        call_count = 0
        seen_review_prompts = []
        seen_fix_prompts = []

        def mock_run(prompt, model, args=None):
            nonlocal call_count
            call_count += 1
            # Round 1: review rejects "missing tests"
            # Round 1: fix runs (gets feedback)
            # Round 2: review rejects "error handling"
            # Round 2: fix runs (gets accumulated feedback) then approves
            if "review" in prompt and "missing tests" not in prompt:
                # Round 1 review
                seen_review_prompts.append(prompt)
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="reject", payload="missing tests")],
                )
            elif "review" in prompt and "missing tests" in prompt:
                # Round 2 review — can see round 1 feedback
                seen_review_prompts.append(prompt)
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="reject", payload="error handling")],
                )
            else:
                # Fix step
                seen_fix_prompts.append(prompt)
                if len(seen_fix_prompts) >= 2:
                    return ExecutorResult(
                        output="out", exit_code=0, error=None,
                        signals=[Signal(type="approve")],
                    )
                return ExecutorResult(
                    output="out", exit_code=0, error=None, signals=[],
                )

        executor = engine.executors.get("claude-code")
        executor.run = mock_run

        heads = iter(["a", "b", "c", "d", "e", "f"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, {})

        # Round 2 fix should see BOTH rounds' feedback
        assert len(seen_fix_prompts) >= 2
        last_fix = seen_fix_prompts[-1]
        assert "missing tests" in last_fix
        assert "error handling" in last_fix
        assert "Round 1" in last_fix
        assert "Round 2" in last_fix


def test_feedback_persisted_to_disk():
    """Each rejection should be written to .pilot/session/reviews/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "review.md")
        with open(prompt_file, "w") as f:
            f.write("review")

        loop_step = LoopStep(
            id="review-fix",
            steps=[AgentStep(id="review", prompt="review.md")],
            until="APPROVE",
            max_rounds=3,
        )
        engine = _make_engine([loop_step], tmpdir)
        engine.config.iteration_delay_ms = 0

        call_count = 0

        def mock_execute(step, loop_vars):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ExecutorResult(
                    output="out", exit_code=0, error=None,
                    signals=[Signal(type="reject", payload="needs work")],
                )
            return ExecutorResult(
                output="out", exit_code=0, error=None,
                signals=[Signal(type="approve")],
            )

        engine._execute_agent = mock_execute

        heads = iter(["a", "b", "c", "d"])
        with patch("pilot.engine.get_head_hash", side_effect=heads):
            engine._run_convergence_loop(loop_step, {})

        reviews_dir = os.path.join(tmpdir, "session", "reviews")
        assert os.path.isdir(reviews_dir)
        files = os.listdir(reviews_dir)
        assert len(files) == 1
        assert "review-fix-round-01.md" in files

        with open(os.path.join(reviews_dir, files[0])) as f:
            content = f.read()
        assert "needs work" in content


def test_format_feedback_single_round():
    """Single rejection should be returned as-is, no headers."""
    result = PipelineEngine._format_feedback([(1, "missing tests")])
    assert result == "missing tests"
    assert "Round" not in result


def test_format_feedback_multiple_rounds():
    """Multiple rejections should be formatted with round headers."""
    result = PipelineEngine._format_feedback([
        (1, "missing tests"),
        (2, "error handling"),
    ])
    assert "### Round 1" in result
    assert "missing tests" in result
    assert "### Round 2" in result
    assert "error handling" in result
