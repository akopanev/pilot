"""Tests for CLI commands: --version, agents, doctor."""

import os
import subprocess
import sys
import tempfile

import pytest
import yaml

from pilot.cli import cmd_agents, cmd_doctor


class FakeArgs:
    def __init__(self, config=None):
        self.config = config


def _write_config(tmpdir, agents=None):
    """Write a minimal pilot.yaml and return its path."""
    config = {
        "version": "1.0",
        "pipeline": [
            {"id": "step1", "agent": {"prompt": "prompts/do.md"}},
        ],
    }
    if agents:
        config["agents"] = agents

    config_path = os.path.join(tmpdir, "pilot.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Create prompt file so validation passes
    prompts_dir = os.path.join(tmpdir, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)
    with open(os.path.join(prompts_dir, "do.md"), "w") as f:
        f.write("do something")

    return config_path


# --- pilot --version ---

def test_version_flag():
    result = subprocess.run(
        [sys.executable, "-m", "pilot", "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "pilot 1.0.0" in result.stdout


def test_version_short_flag():
    result = subprocess.run(
        [sys.executable, "-m", "pilot", "-V"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "pilot 1.0.0" in result.stdout


# --- pilot agents ---

def test_agents_with_yaml_agents(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        config_path = _write_config(tmpdir, agents={
            "reviewer": {
                "prompt": "Review the code",
                "tool": "codex",
                "model": "gpt-4o",
            },
        })
        cmd_agents(FakeArgs(config=config_path))

        out = capsys.readouterr().out
        # 1 YAML agent + 7 built-in agents = 8
        assert "Agents (8 loaded):" in out
        assert "reviewer" in out
        assert "codex" in out
        assert "gpt-4o" in out
        assert "pilot.yaml" in out


def test_agents_no_agents(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        config_path = _write_config(tmpdir)
        cmd_agents(FakeArgs(config=config_path))

        out = capsys.readouterr().out
        # Even with no YAML or file agents, 7 built-in agents are loaded
        assert "Agents (7 loaded):" in out
        assert "built-in" in out


def test_agents_with_file_agents(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        config_path = _write_config(tmpdir)

        # Create a .pilot/agents/ file-based agent (overrides built-in review-quality)
        agents_dir = os.path.join(tmpdir, ".pilot", "agents")
        os.makedirs(agents_dir)
        with open(os.path.join(agents_dir, "review-quality.md"), "w") as f:
            f.write("---\ntool: claude-code\nmodel: claude-sonnet-4\n---\nCheck quality.\n")

        cmd_agents(FakeArgs(config=config_path))

        out = capsys.readouterr().out
        # File-based review-quality overrides built-in review-quality, so still 7 total
        assert "Agents (7 loaded):" in out
        assert "review-quality" in out
        assert ".pilot/agents/review-quality.md" in out


# --- pilot doctor ---

def test_doctor_with_config(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        config_path = _write_config(tmpdir)

        # Create .pilot/session/tasks/
        tasks_dir = os.path.join(tmpdir, ".pilot", "session", "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        with open(os.path.join(tasks_dir, "task1.md"), "w") as f:
            f.write("task 1")

        cmd_doctor(FakeArgs(config=config_path))

        out = capsys.readouterr().out
        assert "pilot doctor" in out
        assert "Python:" in out
        assert "\u2713" in out  # checkmark
        assert "Config:" in out
        assert "1 steps" in out
        assert "Tasks:" in out
        assert "1 files" in out


def test_doctor_no_config(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_doctor(FakeArgs(config=None))

        out = capsys.readouterr().out
        assert "pilot doctor" in out
        assert "not found" in out
        assert "\u2717" in out  # X mark


def test_doctor_python_version(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_doctor(FakeArgs(config=None))

        out = capsys.readouterr().out
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert py_ver in out
