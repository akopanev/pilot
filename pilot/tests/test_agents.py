"""Tests for agent loading — frontmatter parsing and project-local agents."""

import os
import tempfile

from pilot.agents import (
    load_agent_file,
    load_agents,
    parse_frontmatter,
    parse_yaml_agents,
)
from pilot.models import AgentDef


# ── Frontmatter parsing ──────────────────────────────────

def test_parse_frontmatter_basic():
    content = "---\ntool: claude-code\nmodel: claude-sonnet-4\n---\nPrompt body here."
    opts, body = parse_frontmatter(content)
    assert opts == {"tool": "claude-code", "model": "claude-sonnet-4"}
    assert body == "Prompt body here."


def test_parse_frontmatter_no_frontmatter():
    content = "Just a plain prompt with no frontmatter."
    opts, body = parse_frontmatter(content)
    assert opts == {}
    assert body == content


def test_parse_frontmatter_empty_content():
    opts, body = parse_frontmatter("")
    assert opts == {}
    assert body == ""


def test_parse_frontmatter_only_opening():
    content = "---\ntool: codex\nNo closing marker"
    opts, body = parse_frontmatter(content)
    assert opts == {}
    assert body == content


def test_parse_frontmatter_multiline_body():
    content = "---\ntool: codex\n---\nLine 1\nLine 2\nLine 3"
    opts, body = parse_frontmatter(content)
    assert opts == {"tool": "codex"}
    assert body == "Line 1\nLine 2\nLine 3"


def test_parse_frontmatter_with_all_fields():
    content = "---\ntool: custom\nmodel: gpt-4o\nscript: ./run.sh\nretry: 3\n---\nDo stuff."
    opts, body = parse_frontmatter(content)
    assert opts["tool"] == "custom"
    assert opts["model"] == "gpt-4o"
    assert opts["script"] == "./run.sh"
    assert opts["retry"] == 3
    assert body == "Do stuff."


def test_parse_frontmatter_invalid_yaml():
    content = "---\n: invalid: yaml: here:\n---\nBody."
    opts, body = parse_frontmatter(content)
    assert opts == {}
    assert body == content


# ── Agent file loading ────────────────────────────────────

def test_load_agent_file_with_frontmatter():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "reviewer.md")
        with open(path, "w") as f:
            f.write("---\ntool: codex\nmodel: gpt-4o\n---\nReview the code carefully.")
        agent = load_agent_file(path)
        assert agent.name == "reviewer"
        assert agent.tool == "codex"
        assert agent.model == "gpt-4o"
        assert agent.prompt == "Review the code carefully."
        assert agent.script is None
        assert agent.retry is None


def test_load_agent_file_without_frontmatter():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "simple.md")
        with open(path, "w") as f:
            f.write("Just check for bugs.")
        agent = load_agent_file(path)
        assert agent.name == "simple"
        assert agent.prompt == "Just check for bugs."
        assert agent.tool is None
        assert agent.model is None


# ── load_agents (project-local only) ─────────────────────

def test_load_agents_from_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = os.path.join(tmpdir, ".pilot", "agents")
        os.makedirs(agents_dir)
        for name in ("alpha", "beta"):
            with open(os.path.join(agents_dir, f"{name}.md"), "w") as f:
                f.write(f"---\ntool: claude-code\n---\nAgent {name} prompt.")
        agents = load_agents(tmpdir)
        assert len(agents) == 2
        assert "alpha" in agents
        assert "beta" in agents
        assert agents["alpha"].prompt == "Agent alpha prompt."


def test_load_agents_no_dir_returns_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        agents = load_agents(tmpdir)
        assert agents == {}


def test_load_agents_empty_dir_returns_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".pilot", "agents"))
        agents = load_agents(tmpdir)
        assert agents == {}


def test_load_agents_ignores_non_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = os.path.join(tmpdir, ".pilot", "agents")
        os.makedirs(agents_dir)
        with open(os.path.join(agents_dir, "agent.md"), "w") as f:
            f.write("Valid agent.")
        with open(os.path.join(agents_dir, "readme.txt"), "w") as f:
            f.write("Not an agent.")
        agents = load_agents(tmpdir)
        assert len(agents) == 1
        assert "agent" in agents


# ── YAML agents parsing ──────────────────────────────────

def test_parse_yaml_agents_dict_format():
    raw = {
        "reviewer": {
            "prompt": "prompts/review.md",
            "tool": "codex",
            "model": "gpt-4o",
            "retry": 2,
        }
    }
    agents = parse_yaml_agents(raw)
    assert len(agents) == 1
    assert agents["reviewer"].name == "reviewer"
    assert agents["reviewer"].prompt == "prompts/review.md"
    assert agents["reviewer"].tool == "codex"
    assert agents["reviewer"].retry == 2


def test_parse_yaml_agents_shorthand():
    raw = {"quick": "Just check for bugs"}
    agents = parse_yaml_agents(raw)
    assert agents["quick"].prompt == "Just check for bugs"
    assert agents["quick"].tool is None


def test_parse_yaml_agents_missing_prompt_skipped():
    raw = {"bad": {"tool": "codex"}}  # no prompt
    agents = parse_yaml_agents(raw)
    assert len(agents) == 0


def test_parse_yaml_agents_empty():
    assert parse_yaml_agents({}) == {}
    assert parse_yaml_agents(None) == {}


def test_parse_yaml_agents_multiple():
    raw = {
        "a": {"prompt": "Do A"},
        "b": "Do B",
    }
    agents = parse_yaml_agents(raw)
    assert len(agents) == 2
    assert agents["a"].prompt == "Do A"
    assert agents["b"].prompt == "Do B"


# ── Args in agents ───────────────────────────────────────

def test_load_agent_file_with_args():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "strict.md")
        with open(path, "w") as f:
            f.write("---\ntool: codex\nargs:\n  - --sandbox\n  - read-only\n---\nReview carefully.")
        agent = load_agent_file(path)
        assert agent.name == "strict"
        assert agent.args == ["--sandbox", "read-only"]
        assert agent.prompt == "Review carefully."


def test_load_agent_file_without_args():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "simple.md")
        with open(path, "w") as f:
            f.write("---\ntool: codex\n---\nJust review.")
        agent = load_agent_file(path)
        assert agent.args is None


def test_parse_yaml_agents_with_args():
    raw = {
        "reviewer": {
            "prompt": "Review the code.",
            "tool": "codex",
            "args": ["--sandbox", "read-only"],
        }
    }
    agents = parse_yaml_agents(raw)
    assert agents["reviewer"].args == ["--sandbox", "read-only"]


def test_parse_yaml_agents_without_args():
    raw = {"quick": {"prompt": "Quick review"}}
    agents = parse_yaml_agents(raw)
    assert agents["quick"].args is None
