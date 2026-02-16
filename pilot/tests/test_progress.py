"""Tests for progress logging and color output."""

import os
import tempfile

from pilot.progress import (
    BLUE,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    _color_enabled,
    _detect_color,
    colorize,
)


# ── colorize ────────────────────────────────────────────────

def test_colorize():
    result = colorize("hello", GREEN)
    assert result.startswith(GREEN)
    assert result.endswith("\033[0m")
    assert "hello" in result


# ── _detect_color ───────────────────────────────────────────

def test_detect_agent_step():
    assert _detect_color("▸ snapshot (claude-code/claude-sonnet-4)") == GREEN


def test_detect_shell_step():
    assert _detect_color("▸ validate (shell)") == CYAN


def test_detect_loop_step():
    assert _detect_color("▸ dev (loop) — 3 items") == MAGENTA


def test_detect_gate_step():
    assert _detect_color("▸ approval (gate) — waiting for user") == YELLOW


def test_detect_signal():
    assert _detect_color("  signal: approve") == BLUE


def test_detect_nonzero_exit():
    assert _detect_color("  exit_code=1") == RED


def test_detect_zero_exit_not_red():
    assert _detect_color("  exit_code=0") != RED


def test_detect_approve_check():
    assert _detect_color("  ✓ approved at round 2") == GREEN


def test_detect_warning():
    assert _detect_color("  ⚠ max rounds (3) reached") == YELLOW


def test_detect_pipeline_started():
    assert _detect_color("Pipeline started") == GREEN


def test_detect_pipeline_complete():
    assert _detect_color("Pipeline complete") == GREEN


def test_detect_plain_message():
    assert _detect_color("  skipping step1") is None


# ── _color_enabled ──────────────────────────────────────────

def test_color_disabled_by_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert _color_enabled() is False


def test_color_disabled_by_pilot_no_color(monkeypatch):
    monkeypatch.setenv("PILOT_NO_COLOR", "1")
    assert _color_enabled() is False


# ── ProgressLog file output ─────────────────────────────────

def test_progress_log_writes_plain_to_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        from pilot.progress import ProgressLog
        path = os.path.join(tmpdir, "progress.log")
        log = ProgressLog(path)
        log.log("Pipeline started")
        log.close()

        with open(path) as f:
            content = f.read()
        assert "Pipeline started" in content
        # File should never contain ANSI codes
        assert "\033[" not in content
