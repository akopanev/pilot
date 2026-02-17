"""Tests for pilot init command."""

import os
import tempfile
from pathlib import Path

from pilot.cli import cmd_init, get_templates_dir, get_defaults_dir


class FakeArgs:
    def __init__(self, template="develop", list_flag=False):
        self.template = template
        self.list = list_flag


def test_templates_dir_exists():
    d = get_templates_dir()
    assert d.is_dir()


def test_templates_dir_has_templates():
    d = get_templates_dir()
    templates = [e.name for e in d.iterdir() if e.is_dir()]
    assert "develop" in templates


def test_defaults_has_bundled_files():
    """README.md and protocol.md must be in defaults/ for pip install to work."""
    d = get_defaults_dir()
    assert (d / "README.md").is_file()
    assert (d / "protocol.md").is_file()


def test_init_copies_files(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_init(FakeArgs())

        # Template files are copied into .pilot/
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "pipeline.yaml"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "analyze.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "implement.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "claude-implement.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "review.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "codex-review.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "claude-review.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "prompts", "fix.md"))

        # Built-in agents are copied into .pilot/agents/
        agents_dir = os.path.join(tmpdir, ".pilot", "agents")
        assert os.path.isdir(agents_dir)
        agent_files = os.listdir(agents_dir)
        assert len(agent_files) == 10
        for name in ["implementation.md", "quality.md", "testing.md",
                      "simplification.md", "documentation.md",
                      "analyst-pm.md", "analyst-architect.md",
                      "analyst-ux.md", "analyst-qa.md", "analyst-devops.md"]:
            assert name in agent_files

        # README, protocol, and tasks
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "README.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "protocol.md"))
        assert os.path.isdir(os.path.join(tmpdir, ".pilot", "session", "tasks"))


def test_init_creates_pilot_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_init(FakeArgs())

        assert os.path.isdir(os.path.join(tmpdir, ".pilot"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "README.md"))
        assert os.path.isfile(os.path.join(tmpdir, ".pilot", "protocol.md"))
        assert os.path.isdir(os.path.join(tmpdir, ".pilot", "session", "tasks"))


def test_init_readme_has_content(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_init(FakeArgs())

        readme = os.path.join(tmpdir, ".pilot", "README.md")
        with open(readme) as f:
            content = f.read()
        assert "PILOT" in content
        assert len(content) > 100  # not empty


def test_init_does_not_overwrite(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        # Create existing file at .pilot/pipeline.yaml
        pilot_dir = os.path.join(tmpdir, ".pilot")
        os.makedirs(pilot_dir, exist_ok=True)
        with open(os.path.join(pilot_dir, "pipeline.yaml"), "w") as f:
            f.write("existing content")

        cmd_init(FakeArgs())

        # Existing file should not be overwritten
        with open(os.path.join(pilot_dir, "pipeline.yaml")) as f:
            assert f.read() == "existing content"


def test_init_does_not_overwrite_pilot_readme(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        # Pre-create .pilot/README.md
        pilot_dir = os.path.join(tmpdir, ".pilot")
        os.makedirs(pilot_dir)
        with open(os.path.join(pilot_dir, "README.md"), "w") as f:
            f.write("custom docs")

        cmd_init(FakeArgs())

        with open(os.path.join(pilot_dir, "README.md")) as f:
            assert f.read() == "custom docs"


def test_init_unknown_template(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        import pytest
        with pytest.raises(SystemExit):
            cmd_init(FakeArgs(template="nonexistent-template"))


def test_init_list(capsys):
    cmd_init(FakeArgs(list_flag=True))
    out = capsys.readouterr().out
    assert "develop" in out


def test_init_prints_next_steps(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        cmd_init(FakeArgs())

        out = capsys.readouterr().out
        assert "Next steps:" in out
        assert "pilot run" in out
