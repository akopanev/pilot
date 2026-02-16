"""Template variable expansion for prompts."""

from __future__ import annotations

import os
import re

from pilot.models import AgentDef, PilotConfig, QAPair, RuntimeContext


FILE_PATTERN = re.compile(r"\{\{file:(.+?)\}\}")
EMISSION_PATTERN = re.compile(r"\{\{emit\.([^}]+)\}\}")
AGENT_REF_PATTERN = re.compile(r"\{\{agent:([a-zA-Z0-9_-]+)\}\}")
QUESTIONS_PATTERN = re.compile(r"\{\{questions(?::([a-zA-Z0-9_-]+))?\}\}")


def expand_inputs(text: str, inputs: dict[str, str]) -> str:
    """Replace {{var_name}} with values from inputs section."""
    for name, value in inputs.items():
        text = text.replace(f"{{{{{name}}}}}", value)
    return text


def expand_runtime(text: str, runtime: RuntimeContext) -> str:
    """Replace auto-detected variables computed by CLI."""
    replacements = {
        "{{default_branch}}":      runtime.default_branch,
        "{{diff}}":                runtime.diff_command,
        "{{progress_file_path}}":  runtime.progress_path,
        "{{round}}":               str(runtime.round),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def expand_files(text: str, base_dir: str) -> str:
    """Replace {{file:path}} with file contents."""
    def replace_match(m: re.Match) -> str:
        path = os.path.join(base_dir, m.group(1))
        if os.path.isfile(path):
            with open(path) as f:
                return f.read()
        return f"[FILE NOT FOUND: {m.group(1)}]"
    return FILE_PATTERN.sub(replace_match, text)


def expand_loop_vars(text: str, loop_vars: dict[str, str]) -> str:
    """Replace loop-injected vars like {{TASK}}, {{FEEDBACK}}."""
    for name, value in loop_vars.items():
        text = text.replace(f"{{{{{name}}}}}", value)
    return text


def _format_qa(pairs: list[QAPair]) -> str:
    """Format Q&A pairs as markdown, grouped by step_id."""
    if not pairs:
        return ""
    by_step: dict[str, list[QAPair]] = {}
    for qa in pairs:
        by_step.setdefault(qa.step_id, []).append(qa)
    sections = []
    for step_id, step_pairs in by_step.items():
        lines = [f"### {step_id}"]
        for qa in step_pairs:
            lines.append(f"**Q:** {qa.question}")
            lines.append(f"**A:** {qa.answer}")
            lines.append("")
        sections.append("\n".join(lines))
    return "## Prior Q&A\n\n" + "\n".join(sections)


def expand_questions(text: str, questions: list[QAPair]) -> str:
    """Replace {{questions}} or {{questions:step_id}} with formatted Q&A."""
    def replace_match(m: re.Match) -> str:
        step_filter = m.group(1)
        if step_filter:
            filtered = [q for q in questions if q.step_id == step_filter]
        else:
            filtered = questions
        return _format_qa(filtered)
    return QUESTIONS_PATTERN.sub(replace_match, text)


def expand_emissions(text: str, emissions: dict[str, str]) -> str:
    """Replace {{emit.key}} with values from runtime emissions."""
    def replace_match(m: re.Match) -> str:
        key = m.group(1)
        if key in emissions:
            return emissions[key]
        return m.group(0)  # leave unchanged if key not found
    return EMISSION_PATTERN.sub(replace_match, text)


def _format_agent_expansion(name: str, prompt: str, agent: AgentDef) -> str:
    """Wrap agent prompt in Task tool launch instructions.

    Includes model clause if the agent specifies one in frontmatter.
    Matches ralphex's formatAgentExpansion pattern.
    """
    model_clause = ""
    if agent.model:
        model_clause = f" with model={agent.model}"

    return (
        f"Use the Task tool{model_clause} to launch a subagent with this prompt:\n"
        f'"{prompt}"\n\n'
        f"Report findings only — no positive observations."
    )


def expand_agents(text: str, agents: dict[str, AgentDef], base_dir: str) -> str:
    """Replace {{agent:name}} with Task tool launch instructions."""
    def replace_match(m: re.Match) -> str:
        name = m.group(1)
        if name not in agents:
            return m.group(0)  # leave unchanged if agent not found
        agent = agents[name]
        # Load prompt: file path or inline text
        prompt = agent.prompt
        if "\n" not in prompt and prompt.strip().endswith((".md", ".txt")):
            path = os.path.join(base_dir, prompt)
            if os.path.isfile(path):
                with open(path) as f:
                    prompt = f.read()
        return _format_agent_expansion(name, prompt, agent)
    return AGENT_REF_PATTERN.sub(replace_match, text)


def expand_prompt(
    text: str,
    config: PilotConfig,
    runtime: RuntimeContext,
    loop_vars: dict[str, str] | None = None,
) -> str:
    """Apply all template expansions in order."""
    text = expand_inputs(text, config.inputs)
    text = expand_runtime(text, runtime)
    text = expand_files(text, runtime.config_dir)
    if loop_vars:
        text = expand_loop_vars(text, loop_vars)
    text = expand_emissions(text, runtime.emissions)
    text = expand_questions(text, runtime.questions)
    text = expand_agents(text, config.agents, runtime.config_dir)
    return text


def load_prompt(prompt_value: str, base_dir: str) -> str:
    """Load prompt content — file path or inline text."""
    if "\n" in prompt_value or not prompt_value.strip().endswith((".md", ".txt")):
        return prompt_value                 # inline prompt
    path = os.path.join(base_dir, prompt_value)
    with open(path) as f:
        return f.read()
