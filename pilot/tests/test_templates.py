"""Tests for template variable expansion."""

import os
import tempfile

from pilot.models import AgentDef, AgentDefaults, PilotConfig, QAPair, RuntimeContext
from pilot.templates import (
    expand_agents,
    expand_emissions,
    expand_files,
    expand_inputs,
    expand_loop_vars,
    expand_prompt,
    expand_questions,
    expand_runtime,
    load_prompt,
)


def test_expand_inputs():
    text = "Read {{input}} and check {{plan}}"
    inputs = {"input": ".pilot/input.md", "plan": ".pilot/plan.md"}
    result = expand_inputs(text, inputs)
    assert result == "Read .pilot/input.md and check .pilot/plan.md"


def test_expand_inputs_no_match():
    text = "No variables here"
    result = expand_inputs(text, {"foo": "bar"})
    assert result == "No variables here"


def test_expand_runtime():
    runtime = RuntimeContext(
        project_dir="/tmp",
        config_dir="/tmp",
        session_dir="/tmp/session",
        default_branch="main",
        progress_path=".pilot/progress.log",
        diff_command="git diff main...HEAD",
        round=3,
    )
    text = "Branch: {{default_branch}}, Diff: {{diff}}, Round: {{round}}"
    result = expand_runtime(text, runtime)
    assert result == "Branch: main, Diff: git diff main...HEAD, Round: 3"


def test_expand_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file to inject
        test_file = os.path.join(tmpdir, "test.md")
        with open(test_file, "w") as f:
            f.write("file contents here")

        text = "Before {{file:test.md}} after"
        result = expand_files(text, tmpdir)
        assert result == "Before file contents here after"


def test_expand_files_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        text = "Before {{file:missing.md}} after"
        result = expand_files(text, tmpdir)
        assert "[FILE NOT FOUND: missing.md]" in result


def test_expand_loop_vars():
    text = "Task: {{TASK}}, Feedback: {{FEEDBACK}}"
    loop_vars = {"TASK": "do something", "FEEDBACK": "needs work"}
    result = expand_loop_vars(text, loop_vars)
    assert result == "Task: do something, Feedback: needs work"


def test_expand_prompt_full():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file for injection
        agent_file = os.path.join(tmpdir, "agent.md")
        with open(agent_file, "w") as f:
            f.write("agent rules")

        config = PilotConfig(
            version="1.0",
            inputs={"plan": ".pilot/plan.md"},
            defaults=AgentDefaults(),
            pipeline=[],
        )
        runtime = RuntimeContext(
            project_dir=tmpdir,
            config_dir=tmpdir,
            session_dir=os.path.join(tmpdir, "session"),
            default_branch="main",
            progress_path=".pilot/progress.log",
            diff_command="git diff main...HEAD",
            round=1,
        )

        text = "Plan: {{plan}}, Branch: {{default_branch}}, Agent: {{file:agent.md}}"
        result = expand_prompt(text, config, runtime)
        assert result == "Plan: .pilot/plan.md, Branch: main, Agent: agent rules"


def test_load_prompt_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "task.md")
        with open(prompt_file, "w") as f:
            f.write("do the thing")

        result = load_prompt("task.md", tmpdir)
        assert result == "do the thing"


def test_load_prompt_inline():
    result = load_prompt("This is an inline prompt\nwith multiple lines", "/tmp")
    assert result == "This is an inline prompt\nwith multiple lines"


def test_load_prompt_inline_no_extension():
    result = load_prompt("Just do the task", "/tmp")
    assert result == "Just do the task"


# ── Emission expansion tests ─────────────────────────────

def test_expand_emissions_basic():
    text = "API: {{emit.api_url}}"
    result = expand_emissions(text, {"api_url": "https://example.com"})
    assert result == "API: https://example.com"


def test_expand_emissions_multiple_keys():
    text = "URL: {{emit.url}}, Token: {{emit.token}}"
    emissions = {"url": "https://api.com", "token": "abc123"}
    result = expand_emissions(text, emissions)
    assert result == "URL: https://api.com, Token: abc123"


def test_expand_emissions_missing_key_unchanged():
    text = "Value: {{emit.missing}}"
    result = expand_emissions(text, {"other": "val"})
    assert result == "Value: {{emit.missing}}"


def test_expand_emissions_empty_dict():
    text = "Value: {{emit.key}}"
    result = expand_emissions(text, {})
    assert result == "Value: {{emit.key}}"


def test_expand_emissions_multiline_value():
    text = "Config:\n{{emit.cfg}}"
    result = expand_emissions(text, {"cfg": "line1\nline2\nline3"})
    assert result == "Config:\nline1\nline2\nline3"


def test_expand_prompt_with_emissions():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = PilotConfig(
            version="1.0",
            inputs={},
            defaults=AgentDefaults(),
            pipeline=[],
        )
        runtime = RuntimeContext(
            project_dir=tmpdir,
            config_dir=tmpdir,
            session_dir=os.path.join(tmpdir, "session"),
            default_branch="main",
            progress_path=".pilot/progress.log",
            diff_command="git diff main...HEAD",
            round=1,
            emissions={"api_url": "https://api.example.com"},
        )

        text = "URL: {{emit.api_url}}, Branch: {{default_branch}}"
        result = expand_prompt(text, config, runtime)
        assert result == "URL: https://api.example.com, Branch: main"


# ── Agent expansion tests ────────────────────────────────

def test_expand_agents_inline_prompt():
    agents = {"reviewer": AgentDef(name="reviewer", prompt="Check the code for bugs.")}
    text = "Review:\n{{agent:reviewer}}"
    result = expand_agents(text, agents, "/tmp")
    assert "Use the Task tool" in result
    assert "Check the code for bugs." in result
    assert "Report findings only" in result


def test_expand_agents_unknown_agent_unchanged():
    agents = {}
    text = "Use {{agent:nonexistent}} here"
    result = expand_agents(text, agents, "/tmp")
    assert result == "Use {{agent:nonexistent}} here"


def test_expand_agents_file_prompt():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = os.path.join(tmpdir, "review.md")
        with open(prompt_file, "w") as f:
            f.write("File-based review prompt content")
        agents = {"review": AgentDef(name="review", prompt="review.md")}
        text = "Instructions:\n{{agent:review}}"
        result = expand_agents(text, agents, tmpdir)
        assert "Use the Task tool" in result
        assert "File-based review prompt content" in result


def test_expand_agents_multiple():
    agents = {
        "a": AgentDef(name="a", prompt="Agent A"),
        "b": AgentDef(name="b", prompt="Agent B"),
    }
    text = "First: {{agent:a}}, Second: {{agent:b}}"
    result = expand_agents(text, agents, "/tmp")
    assert "Agent A" in result
    assert "Agent B" in result
    assert result.count("Use the Task tool") == 2


def test_expand_agents_with_hyphens_underscores():
    agents = {"my-agent_v2": AgentDef(name="my-agent_v2", prompt="Special agent")}
    text = "Use {{agent:my-agent_v2}}"
    result = expand_agents(text, agents, "/tmp")
    assert "Special agent" in result
    assert "Use the Task tool" in result


def test_expand_agents_with_model():
    """Agent with model in frontmatter should include model clause."""
    agents = {"quality": AgentDef(name="quality", prompt="Check quality.", model="opus")}
    text = "{{agent:quality}}"
    result = expand_agents(text, agents, "/tmp")
    assert "with model=opus" in result
    assert "Check quality." in result


def test_expand_agents_without_model():
    """Agent without model should have no model clause."""
    agents = {"quality": AgentDef(name="quality", prompt="Check quality.")}
    text = "{{agent:quality}}"
    result = expand_agents(text, agents, "/tmp")
    assert "with model=" not in result
    assert "Use the Task tool to launch" in result


def test_expand_prompt_with_agents():
    with tempfile.TemporaryDirectory() as tmpdir:
        agents = {"quality": AgentDef(name="quality", prompt="Check quality.")}
        config = PilotConfig(
            version="1.0",
            inputs={},
            defaults=AgentDefaults(),
            pipeline=[],
            agents=agents,
        )
        runtime = RuntimeContext(
            project_dir=tmpdir,
            config_dir=tmpdir,
            session_dir=os.path.join(tmpdir, "session"),
            default_branch="main",
            progress_path=".pilot/progress.log",
            diff_command="git diff main...HEAD",
            round=1,
        )

        text = "Review with {{agent:quality}}, branch: {{default_branch}}"
        result = expand_prompt(text, config, runtime)
        assert "Use the Task tool" in result
        assert "Check quality." in result
        assert "main" in result


# ── Questions expansion tests ─────────────────────────────

def test_expand_questions_all():
    questions = [
        QAPair(step_id="prd", question="Which DB?", answer="PostgreSQL"),
        QAPair(step_id="plan", question="Monorepo?", answer="Yes"),
    ]
    text = "Context:\n{{questions}}"
    result = expand_questions(text, questions)
    assert "## Prior Q&A" in result
    assert "### prd" in result
    assert "**Q:** Which DB?" in result
    assert "**A:** PostgreSQL" in result
    assert "### plan" in result
    assert "**Q:** Monorepo?" in result


def test_expand_questions_filtered_by_step():
    questions = [
        QAPair(step_id="prd", question="Which DB?", answer="PostgreSQL"),
        QAPair(step_id="plan", question="Monorepo?", answer="Yes"),
    ]
    text = "{{questions:prd}}"
    result = expand_questions(text, questions)
    assert "### prd" in result
    assert "Which DB?" in result
    assert "Monorepo?" not in result


def test_expand_questions_empty():
    text = "Context:\n{{questions}}"
    result = expand_questions(text, [])
    assert result == "Context:\n"


def test_expand_questions_filter_no_match():
    questions = [QAPair(step_id="prd", question="Q?", answer="A")]
    text = "{{questions:nonexistent}}"
    result = expand_questions(text, questions)
    assert result == ""


def test_expand_questions_multiple_per_step():
    questions = [
        QAPair(step_id="prd", question="Q1?", answer="A1"),
        QAPair(step_id="prd", question="Q2?", answer="A2"),
    ]
    text = "{{questions:prd}}"
    result = expand_questions(text, questions)
    assert "**Q:** Q1?" in result
    assert "**Q:** Q2?" in result
    assert result.count("### prd") == 1


def test_expand_prompt_with_questions():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = PilotConfig(
            version="1.0",
            inputs={},
            defaults=AgentDefaults(),
            pipeline=[],
        )
        runtime = RuntimeContext(
            project_dir=tmpdir,
            config_dir=tmpdir,
            session_dir=os.path.join(tmpdir, "session"),
            default_branch="main",
            progress_path=".pilot/progress.log",
            diff_command="git diff main...HEAD",
            round=1,
            questions=[QAPair(step_id="prd", question="DB?", answer="Postgres")],
        )

        text = "Branch: {{default_branch}}\n{{questions}}"
        result = expand_prompt(text, config, runtime)
        assert "Branch: main" in result
        assert "**Q:** DB?" in result
        assert "**A:** Postgres" in result
