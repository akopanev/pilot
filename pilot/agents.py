"""Agent loading — frontmatter parsing and project-local agent files."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from pilot.models import AgentDef


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from agent file content.

    Format:
        ---
        tool: claude-code
        model: claude-sonnet-4
        ---
        Prompt body here...

    Returns (options_dict, body). If no frontmatter, returns ({}, original content).
    """
    if not content.startswith("---\n"):
        return {}, content

    # Find closing ---
    rest = content[4:]  # skip opening ---\n
    idx = rest.find("\n---")
    if idx == -1:
        return {}, content

    header = rest[:idx]
    body = rest[idx + 4:]  # skip \n---
    if body and body[0] == '\n':
        body = body[1:]

    try:
        opts = yaml.safe_load(header) or {}
    except yaml.YAMLError:
        return {}, content

    return opts, body.strip()


def load_agent_file(path: str) -> AgentDef:
    """Load a single agent .md file with optional frontmatter."""
    name = Path(path).stem
    with open(path) as f:
        content = f.read()

    opts, body = parse_frontmatter(content)

    return AgentDef(
        name=name,
        prompt=body,
        tool=opts.get("tool"),
        model=opts.get("model"),
        script=opts.get("script"),
        retry=opts.get("retry"),
        args=opts.get("args"),
        source=path,
    )


def load_builtin_agents() -> dict[str, AgentDef]:
    """Load built-in agent .md files from the package defaults."""
    agents_dir = os.path.join(os.path.dirname(__file__), "defaults", "agents")
    agents = {}
    if not os.path.isdir(agents_dir):
        return agents
    for filename in sorted(os.listdir(agents_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(agents_dir, filename)
        if os.path.isfile(filepath):
            agent = load_agent_file(filepath)
            agent.source = "built-in"
            agents[agent.name] = agent
    return agents


def load_agents(project_dir: str) -> dict[str, AgentDef]:
    """Load agent .md files from .pilot/agents/ if the directory exists."""
    agents_dir = os.path.join(project_dir, ".pilot", "agents")
    agents = {}
    if not os.path.isdir(agents_dir):
        return agents

    for filename in sorted(os.listdir(agents_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(agents_dir, filename)
        if os.path.isfile(filepath):
            agent = load_agent_file(filepath)
            agents[agent.name] = agent

    return agents


def parse_yaml_agents(raw_agents: dict) -> dict[str, AgentDef]:
    """Parse agents: section from pilot.yaml.

    Format:
        agents:
          reviewer:
            prompt: prompts/review.md    # or inline text
            tool: codex
            model: gpt-4o
            retry: 2
          quick:
            prompt: "Just check for bugs"
    """
    agents = {}
    if not raw_agents:
        return agents

    for name, value in raw_agents.items():
        if isinstance(value, str):
            # Shorthand: agents: { name: "prompt text or path" }
            agents[name] = AgentDef(name=name, prompt=value, source="pilot.yaml")
        elif isinstance(value, dict):
            if "prompt" not in value:
                continue  # skip invalid entries
            agents[name] = AgentDef(
                name=name,
                prompt=value["prompt"],
                tool=value.get("tool"),
                model=value.get("model"),
                script=value.get("script"),
                retry=value.get("retry"),
                args=value.get("args"),
                source="pilot.yaml",
            )

    return agents
