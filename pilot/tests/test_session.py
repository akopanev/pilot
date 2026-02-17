"""Tests for session management: session.json and emissions persistence."""

import json
import os
import tempfile
from unittest.mock import patch

from pilot.engine import PipelineEngine
from pilot.models import (
    AgentDefaults,
    AgentStep,
    PilotConfig,
    RuntimeContext,
    ShellStep,
)
from pilot.session import Session
from pilot.signals import Signal


def _make_engine(steps, tmpdir, emissions=None):
    config = PilotConfig(
        version="1.0",
        inputs={},
        defaults=AgentDefaults(),
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
        emissions=emissions or {},
    )
    return PipelineEngine(config, runtime)


# ── Session class ─────────────────────────────────────


def test_session_new_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        assert session.completed == []
        assert session.current is None
        assert session.branch is None


def test_session_start_writes_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.start()

        path = os.path.join(tmpdir, "session.json")
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["started_at"] is not None
        assert data["completed"] == []


def test_session_mark_current():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.mark_current("analyze")

        reloaded = Session(tmpdir)
        assert reloaded.current == "analyze"


def test_session_mark_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.mark_current("analyze")
        session.mark_done("analyze")

        reloaded = Session(tmpdir)
        assert "analyze" in reloaded.completed
        assert reloaded.current is None


def test_session_is_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        assert not session.is_done("analyze")
        session.mark_done("analyze")
        assert session.is_done("analyze")


def test_session_preserves_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.mark_done("analyze")
        session.mark_done("prd")
        session.mark_done("plan")

        reloaded = Session(tmpdir)
        assert reloaded.completed == ["analyze", "prd", "plan"]


def test_session_no_duplicate_completed():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.mark_done("analyze")
        session.mark_done("analyze")
        assert session.completed == ["analyze"]


def test_session_set_branch():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        session.set_branch("pilot/my-feature")

        reloaded = Session(tmpdir)
        assert reloaded.branch == "pilot/my-feature"


def test_session_load_nonexistent():
    """Session should not crash if session.json doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(tmpdir)
        assert session.completed == []
        assert not session.is_done("anything")


# ── Emissions persistence ─────────────────────────────


def test_save_emission_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)
        engine._save_emission("snapshot", "# Project Snapshot\nDetails here.")

        emission_path = os.path.join(tmpdir, "session", "emissions", "snapshot.md")
        assert os.path.isfile(emission_path)
        with open(emission_path) as f:
            assert f.read() == "# Project Snapshot\nDetails here."


def test_load_emissions_on_startup():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pre-create emissions directory with files (inside session/)
        emissions_dir = os.path.join(tmpdir, "session", "emissions")
        os.makedirs(emissions_dir)
        with open(os.path.join(emissions_dir, "snapshot.md"), "w") as f:
            f.write("cached snapshot")
        with open(os.path.join(emissions_dir, "prd.md"), "w") as f:
            f.write("cached prd")

        engine = _make_engine([], tmpdir)

        assert engine.runtime.emissions["snapshot"] == "cached snapshot"
        assert engine.runtime.emissions["prd"] == "cached prd"


def test_load_emissions_ignores_non_md_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        emissions_dir = os.path.join(tmpdir, "session", "emissions")
        os.makedirs(emissions_dir)
        with open(os.path.join(emissions_dir, "snapshot.md"), "w") as f:
            f.write("good")
        with open(os.path.join(emissions_dir, ".gitkeep"), "w") as f:
            f.write("")

        engine = _make_engine([], tmpdir)
        assert "snapshot" in engine.runtime.emissions
        assert ".gitkeep" not in engine.runtime.emissions


def test_load_emissions_no_dir():
    """Engine should not crash if emissions dir doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)
        assert engine.runtime.emissions == {}


def test_emit_signal_persists_to_disk():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine([], tmpdir)

        signals = [Signal(type="emit", key="api_url", payload="https://api.com")]
        engine.handle_signals(signals, "setup")

        # In memory
        assert engine.runtime.emissions["api_url"] == "https://api.com"
        # On disk
        emission_path = os.path.join(tmpdir, "session", "emissions", "api_url.md")
        assert os.path.isfile(emission_path)
        with open(emission_path) as f:
            assert f.read() == "https://api.com"


# ── Engine integration with session ───────────────────


def test_run_skips_completed_steps():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
            ShellStep(id="step3", command="echo 3"),
        ]
        engine = _make_engine(steps, tmpdir)

        # Pre-mark step1 as done via session
        engine.session.mark_done("step1")

        executed = []
        original_run_shell = engine.run_shell

        def tracking_run_shell(step, loop_vars):
            executed.append(step.id)
            return original_run_shell(step, loop_vars)

        engine.run_shell = tracking_run_shell
        engine.run()

        assert "step1" not in executed
        assert "step2" in executed
        assert "step3" in executed


def test_run_marks_steps_done_in_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
        ]
        engine = _make_engine(steps, tmpdir)
        engine.run()

        assert engine.session.is_done("step1")
        assert engine.session.is_done("step2")

        # Verify session.json on disk (inside session/)
        with open(os.path.join(tmpdir, "session", "session.json")) as f:
            data = json.load(f)
        assert data["completed"] == ["step1", "step2"]
        assert data["current"] is None
        assert data["started_at"] is not None


def test_run_tracks_current_step():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
        ]
        engine = _make_engine(steps, tmpdir)

        current_during = []
        original_run_shell = engine.run_shell

        def tracking_run_shell(step, loop_vars):
            current_during.append(engine.session.current)
            return original_run_shell(step, loop_vars)

        engine.run_shell = tracking_run_shell
        engine.run()

        assert current_during == ["step1", "step2"]


def test_resume_marks_steps_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        steps = [
            ShellStep(id="step1", command="echo 1"),
            ShellStep(id="step2", command="echo 2"),
            ShellStep(id="step3", command="echo 3"),
        ]
        engine = _make_engine(steps, tmpdir)
        engine.resume_from("step2")

        # step1 was skipped, not marked done
        assert not engine.session.is_done("step1")
        # step2 and step3 ran and should be marked done
        assert engine.session.is_done("step2")
        assert engine.session.is_done("step3")
