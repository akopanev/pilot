"""Tests for YAML config parsing."""

import os
import tempfile

import pytest

from pilot.config import ConfigError, load_config
from pilot.models import AgentStep, GateStep, LoopStep, ShellStep


MINIMAL_CONFIG = """\
version: "1.0"
pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
"""

FULL_CONFIG = """\
version: "1.0"

inputs:
  input: .pilot/input.md
  plan: .pilot/plan.md

defaults:
  agent:
    tool: claude-code
    model: claude-sonnet-4

pipeline:
  - id: snapshot
    agent:
      prompt: prompts/snapshot.md

  - id: validate
    shell:
      command: python validate.py

  - id: approval
    gate: {}

  - id: dev
    loop:
      over: .pilot/tasks/
      as: TASK
      order: asc
    steps:
      - id: execute
        agent:
          prompt: prompts/execute.md
      - id: review-loop
        loop:
          until: APPROVE
          max_rounds: 3
        steps:
          - id: review
            agent:
              prompt: prompts/review.md
"""

SHORTHAND_CONFIG = """\
version: "1.0"
pipeline:
  - id: task
    agent: prompts/task.md
  - id: lint
    shell: npm run lint
"""


def _write_config(tmpdir: str, content: str) -> str:
    path = os.path.join(tmpdir, "pilot.yaml")
    with open(path, "w") as f:
        f.write(content)
    return path


def test_load_minimal():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.version == "1.0"
        assert len(config.pipeline) == 1
        assert isinstance(config.pipeline[0], AgentStep)
        assert config.pipeline[0].id == "step1"


def test_load_full():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, FULL_CONFIG)
        config = load_config(path)

        assert config.inputs["input"] == ".pilot/input.md"
        assert config.defaults.tool == "claude-code"
        assert config.defaults.model == "claude-sonnet-4"

        assert len(config.pipeline) == 4

        # Agent step
        assert isinstance(config.pipeline[0], AgentStep)
        assert config.pipeline[0].id == "snapshot"

        # Shell step
        assert isinstance(config.pipeline[1], ShellStep)
        assert config.pipeline[1].command == "python validate.py"

        # Gate step
        assert isinstance(config.pipeline[2], GateStep)

        # Loop step with nested convergence loop
        loop = config.pipeline[3]
        assert isinstance(loop, LoopStep)
        assert loop.over == ".pilot/tasks/"
        assert loop.as_var == "TASK"
        assert len(loop.steps) == 2

        inner_loop = loop.steps[1]
        assert isinstance(inner_loop, LoopStep)
        assert inner_loop.until == "APPROVE"
        assert inner_loop.max_rounds == 3


def test_shorthand_syntax():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, SHORTHAND_CONFIG)
        config = load_config(path)

        assert isinstance(config.pipeline[0], AgentStep)
        assert config.pipeline[0].prompt == "prompts/task.md"

        assert isinstance(config.pipeline[1], ShellStep)
        assert config.pipeline[1].command == "npm run lint"


def test_missing_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, "pipeline:\n  - id: x\n    agent: p.md\n")
        with pytest.raises(ConfigError, match="version"):
            load_config(path)


def test_missing_step_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, 'version: "1.0"\npipeline:\n  - agent: p.md\n')
        with pytest.raises(ConfigError, match="id"):
            load_config(path)


def test_unknown_step_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, 'version: "1.0"\npipeline:\n  - id: x\n    foo: bar\n')
        with pytest.raises(ConfigError, match="Unknown step type"):
            load_config(path)


def test_defaults_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.defaults.tool == "claude-code"
        assert config.defaults.model == "claude-sonnet-4"


# ── Change 1: error_patterns ───────────────────────────────

ERROR_PATTERNS_CONFIG = """\
version: "1.0"
defaults:
  error_patterns: ["rate limit", "quota exceeded"]
pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
"""


def test_error_patterns_parsed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, ERROR_PATTERNS_CONFIG)
        config = load_config(path)
        assert config.error_patterns == ["rate limit", "quota exceeded"]


def test_error_patterns_default_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.error_patterns == []


# ── Change 3: iteration_delay_ms ───────────────────────────

DELAY_CONFIG = """\
version: "1.0"
defaults:
  iteration_delay_ms: 5000
pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
"""


def test_iteration_delay_parsed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, DELAY_CONFIG)
        config = load_config(path)
        assert config.iteration_delay_ms == 5000


def test_iteration_delay_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.iteration_delay_ms == 2000


# ── Change 2: retry ────────────────────────────────────────

RETRY_CONFIG = """\
version: "1.0"
defaults:
  agent:
    retry: 1
pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
      retry: 3
  - id: step2
    agent:
      prompt: prompts/other.md
"""


def test_retry_parsed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, RETRY_CONFIG)
        config = load_config(path)
        assert config.defaults.retry == 1
        assert config.pipeline[0].retry == 3
        assert config.pipeline[1].retry is None  # inherits from defaults


def test_retry_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.defaults.retry == 0


# ── Change 6: custom script ────────────────────────────────

CUSTOM_SCRIPT_CONFIG = """\
version: "1.0"
pipeline:
  - id: custom-review
    agent:
      tool: custom
      script: ./scripts/review.sh
      prompt: prompts/review.md
"""


def test_custom_script_parsed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, CUSTOM_SCRIPT_CONFIG)
        config = load_config(path)
        step = config.pipeline[0]
        assert isinstance(step, AgentStep)
        assert step.tool == "custom"
        assert step.script == "./scripts/review.sh"
        assert step.prompt == "prompts/review.md"


# ── Validation ──────────────────────────────────────────────

def test_duplicate_step_ids():
    cfg = """\
version: "1.0"
pipeline:
  - id: step1
    agent:
      prompt: prompts/a.md
  - id: step1
    agent:
      prompt: prompts/b.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="Duplicate step id"):
            load_config(path)


def test_loop_missing_over_and_until():
    cfg = """\
version: "1.0"
pipeline:
  - id: bad-loop
    loop: {}
    steps:
      - id: child
        agent:
          prompt: prompts/a.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="must have 'over' or 'until'"):
            load_config(path)


def test_iterator_loop_missing_as():
    cfg = """\
version: "1.0"
pipeline:
  - id: bad-loop
    loop:
      over: .pilot/tasks/
    steps:
      - id: child
        agent:
          prompt: prompts/a.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="requires 'as' variable"):
            load_config(path)


def test_loop_no_children():
    cfg = """\
version: "1.0"
pipeline:
  - id: empty-loop
    loop:
      until: APPROVE
    steps: []
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="has no child steps"):
            load_config(path)


def test_custom_tool_without_script():
    cfg = """\
version: "1.0"
pipeline:
  - id: bad-custom
    agent:
      tool: custom
      prompt: prompts/a.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="no 'script' provided"):
            load_config(path)


# ── Agent references ──────────────────────────────────────

AGENT_REF_CONFIG = """\
version: "1.0"

agents:
  reviewer:
    prompt: "Review the code for issues."
    tool: codex
    model: gpt-4o
    retry: 2

pipeline:
  - id: review
    agent: "@reviewer"
"""


def test_agent_ref_resolved():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, AGENT_REF_CONFIG)
        config = load_config(path)
        step = config.pipeline[0]
        assert isinstance(step, AgentStep)
        assert step.prompt == "Review the code for issues."
        assert step.tool == "codex"
        assert step.model == "gpt-4o"
        assert step.retry == 2


def test_agent_ref_step_overrides():
    cfg = """\
version: "1.0"

agents:
  reviewer:
    prompt: "Review the code."
    tool: codex
    model: gpt-4o

pipeline:
  - id: review
    agent:
      prompt: "@reviewer"
      tool: claude-code
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        step = config.pipeline[0]
        # Step-level tool overrides agent's tool
        assert step.tool == "claude-code"
        # Agent's model is used since step doesn't set one
        assert step.model == "gpt-4o"
        # Prompt comes from the agent
        assert step.prompt == "Review the code."


def test_agent_ref_unknown_raises():
    cfg = """\
version: "1.0"
pipeline:
  - id: bad
    agent: "@nonexistent"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        with pytest.raises(ConfigError, match="unknown agent '@nonexistent'"):
            load_config(path)


def test_agent_ref_in_loop():
    cfg = """\
version: "1.0"

agents:
  impl:
    prompt: "Implement the feature."

pipeline:
  - id: dev
    loop:
      over: tasks/
      as: TASK
    steps:
      - id: execute
        agent: "@impl"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        loop = config.pipeline[0]
        assert isinstance(loop, LoopStep)
        step = loop.steps[0]
        assert step.prompt == "Implement the feature."


def test_yaml_agents_section_parsed():
    cfg = """\
version: "1.0"

agents:
  quick:
    prompt: "Quick review"
  thorough:
    prompt: "Thorough review"
    tool: codex

pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        assert "quick" in config.agents
        assert "thorough" in config.agents
        assert config.agents["thorough"].tool == "codex"


def test_agents_yaml_overrides_file_agents():
    """YAML agents section should override file-based agents of same name."""
    cfg = """\
version: "1.0"

agents:
  reviewer:
    prompt: "YAML reviewer prompt"

pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file-based agent with the same name
        agents_dir = os.path.join(tmpdir, ".pilot", "agents")
        os.makedirs(agents_dir)
        with open(os.path.join(agents_dir, "reviewer.md"), "w") as f:
            f.write("File-based reviewer prompt")

        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        # YAML agent should override the file-based agent
        assert config.agents["reviewer"].prompt == "YAML reviewer prompt"


def test_agent_shorthand_syntax():
    """Agent step shorthand with @ reference."""
    cfg = """\
version: "1.0"
agents:
  task-runner:
    prompt: "Run the task"
pipeline:
  - id: run
    agent: "@task-runner"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        assert config.pipeline[0].prompt == "Run the task"


# ── Args field ──────────────────────────────────────────────

ARGS_CONFIG = """\
version: "1.0"
defaults:
  agent:
    args: ["--verbose", "--timeout=60"]
pipeline:
  - id: step1
    agent:
      prompt: prompts/task.md
      args: ["--sandbox", "read-only"]
  - id: step2
    agent:
      prompt: prompts/other.md
"""


def test_args_parsed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, ARGS_CONFIG)
        config = load_config(path)
        assert config.defaults.args == ["--verbose", "--timeout=60"]
        assert config.pipeline[0].args == ["--sandbox", "read-only"]
        assert config.pipeline[1].args is None  # inherits from defaults at runtime


def test_args_default_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, MINIMAL_CONFIG)
        config = load_config(path)
        assert config.defaults.args == []


def test_args_from_agent_ref():
    cfg = """\
version: "1.0"
agents:
  reviewer:
    prompt: "Review the code."
    args: ["--sandbox", "read-only"]
pipeline:
  - id: review
    agent: "@reviewer"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        step = config.pipeline[0]
        assert step.args == ["--sandbox", "read-only"]


def test_args_step_overrides_agent_ref():
    cfg = """\
version: "1.0"
agents:
  reviewer:
    prompt: "Review the code."
    args: ["--sandbox", "read-only"]
pipeline:
  - id: review
    agent:
      prompt: "@reviewer"
      args: ["--sandbox", "full-auto"]
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_config(tmpdir, cfg)
        config = load_config(path)
        step = config.pipeline[0]
        assert step.args == ["--sandbox", "full-auto"]
