"""CLI entry point — pilot run / pilot validate / pilot steps."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import threading
import time
from pathlib import Path

import glob as globmod

from pilot import __version__
from pilot.config import ConfigError, load_config
from pilot.engine import PipelineEngine, PipelineError
from pilot.git import (
    create_branch,
    derive_branch_name,
    get_current_branch,
    get_default_branch,
    get_diff_command,
    is_on_default_branch,
)
from pilot.models import AgentDefaults, AgentStep, GateStep, LoopStep, RuntimeContext, ShellStep
from pilot.session import Session


def print_step_tree(steps, indent: int = 0, defaults: AgentDefaults | None = None,
                    project_dir: str | None = None) -> None:
    """Pretty-print the pipeline step tree with resolved details."""
    prefix = "  " * indent
    for step in steps:
        if isinstance(step, AgentStep):
            tool = step.tool or (defaults.tool if defaults else "claude-code")
            model = step.model or (defaults.model if defaults else "claude-sonnet-4")
            parts = [f"{prefix}▸ {step.id} [agent {tool}/{model}]"]
            if step.script:
                parts.append(f"{prefix}    script: {step.script}")
            retry = step.retry if step.retry is not None else (defaults.retry if defaults else 0)
            if retry > 0:
                parts.append(f"{prefix}    retry: {retry}")
            if project_dir:
                # Resolve prompt relative to .pilot/ (config dir)
                config_dir = os.path.join(project_dir, ".pilot")
                prompt_path = os.path.join(config_dir, step.prompt)
                exists = os.path.isfile(prompt_path)
                status = "ok" if exists else "MISSING"
                parts.append(f"{prefix}    prompt: {step.prompt} ({status})")
            print("\n".join(parts))
        elif isinstance(step, ShellStep):
            print(f"{prefix}▸ {step.id} [shell] {step.command}")
        elif isinstance(step, GateStep):
            print(f"{prefix}⏸ {step.id} [gate]")
        elif isinstance(step, LoopStep):
            if step.over:
                file_count = 0
                if project_dir:
                    pattern = os.path.join(project_dir, step.over, "*.md")
                    file_count = len(globmod.glob(pattern))
                count_info = f" ({file_count} files)" if project_dir else ""
                print(f"{prefix}↻ {step.id} [loop over={step.over} as={step.as_var}]{count_info}")
            elif step.until:
                print(f"{prefix}↻ {step.id} [loop until={step.until} max={step.max_rounds}]")
            print_step_tree(step.steps, indent + 1, defaults=defaults,
                           project_dir=project_dir)


DEFAULT_CONFIG = os.path.join(".pilot", "pipeline.yaml")


def _resolve_branch(args, config) -> str | None:
    """Determine branch name for this run. Returns None if branching is disabled."""
    if args.no_branch:
        return None

    current = get_current_branch()
    if current is None:
        # Not a git repo or git unavailable — skip branching
        return None

    # Already on a feature branch — keep it
    if not is_on_default_branch():
        return current

    # Explicit --branch flag
    if args.branch:
        return args.branch

    # Derive from input file
    input_file = config.inputs.get("input_file", "input.md")
    input_path = os.path.join(".pilot", input_file)
    return derive_branch_name(input_path)


def cmd_run(args) -> None:
    if args.no_color:
        os.environ["PILOT_NO_COLOR"] = "1"

    config = load_config(args.config)
    default_branch = get_default_branch()

    config_dir = os.path.dirname(os.path.abspath(args.config))
    session_dir = os.path.join(config_dir, "session")
    os.makedirs(session_dir, exist_ok=True)

    progress_path = os.path.join(session_dir, f"progress-{int(time.time())}.log")

    runtime = RuntimeContext(
        project_dir=os.getcwd(),
        config_dir=config_dir,
        session_dir=session_dir,
        default_branch=default_branch,
        progress_path=progress_path,
        diff_command=get_diff_command(default_branch, is_first=True),
        round=0,
        debug=args.debug is not None or bool(os.environ.get("PILOT_DEBUG")),
        debug_truncate=int(args.debug or os.environ.get("PILOT_DEBUG_TRUNCATE", "80")),
    )

    if args.dry_run:
        print("Dry run — steps that would execute:\n")
        # Branch info
        branch = _resolve_branch(args, config)
        if branch:
            current = get_current_branch()
            if current and current != default_branch:
                print(f"Branch: {current} (already on feature branch)")
            else:
                print(f"Branch: {branch} (will create)")
        else:
            print("Branch: disabled (--no-branch)")
        print()
        # Config summary
        if config.inputs:
            print("Inputs:")
            for k, v in config.inputs.items():
                print(f"  {k}: {v}")
        print(f"Defaults: tool={config.defaults.tool} model={config.defaults.model}"
              f" retry={config.defaults.retry}")
        if config.error_patterns:
            print(f"Error patterns: {config.error_patterns}")
        print(f"Iteration delay: {config.iteration_delay_ms}ms")
        print()
        print_step_tree(config.pipeline, defaults=config.defaults,
                        project_dir=runtime.project_dir)
        return

    # Session + branch
    session = Session(session_dir)
    branch = _resolve_branch(args, config)
    if branch and is_on_default_branch():
        ok, err = create_branch(branch)
        if ok:
            session.set_branch(branch)
        else:
            print(f"Warning: could not create branch '{branch}': {err}", file=sys.stderr)
            branch = get_current_branch()
    elif branch:
        session.set_branch(branch)

    # Startup banner
    from pilot.progress import colorize, GRAY, GREEN, RESET, _color_enabled
    use_color = _color_enabled()
    def _banner(label, value):
        if use_color:
            return f"  {colorize(label, GRAY)} {value}"
        return f"  {label} {value}"
    print()
    print(_banner("branch:", branch or default_branch))
    print(_banner("progress:", progress_path))
    step_count = len(config.pipeline)
    print(_banner("pipeline:", f"{step_count} steps, delay={config.iteration_delay_ms}ms"))
    print()

    cancel_event = threading.Event()

    def _handle_signal(signum, frame):
        cancel_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    engine = PipelineEngine(config, runtime, cancel_event=cancel_event)

    if args.from_step:
        engine.resume_from(args.from_step)
    else:
        engine.run()


def cmd_validate(args) -> None:
    config_path = args.config or DEFAULT_CONFIG
    config = load_config(config_path)
    print(f"✓ Valid: {len(config.pipeline)} steps")


def cmd_steps(args) -> None:
    config_path = args.config or DEFAULT_CONFIG
    config = load_config(config_path)
    print_step_tree(config.pipeline, defaults=config.defaults,
                    project_dir=os.getcwd())


def get_templates_dir() -> Path:
    """Return path to built-in pipeline templates."""
    return Path(__file__).parent / "defaults" / "templates"


def get_defaults_dir() -> Path:
    """Return path to built-in defaults (bundled package data)."""
    return Path(__file__).parent / "defaults"


def cmd_init(args) -> None:
    templates_dir = get_templates_dir()

    if args.list:
        print("Available templates:\n")
        for entry in sorted(templates_dir.iterdir()):
            if entry.is_dir():
                yaml_path = entry / "pipeline.yaml"
                desc = ""
                if yaml_path.exists():
                    # Read first comment line as description
                    for line in yaml_path.read_text().splitlines():
                        if line.startswith("#"):
                            desc = line.lstrip("# ").strip()
                            break
                print(f"  {entry.name}" + (f"  — {desc}" if desc else ""))
        return

    template_name = args.template
    template_path = templates_dir / template_name

    if not template_path.is_dir():
        available = [e.name for e in templates_dir.iterdir() if e.is_dir()]
        print(f"Unknown template: '{template_name}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(available))}", file=sys.stderr)
        sys.exit(1)

    pilot_dir = Path.cwd() / ".pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    skipped = []

    # Copy template files (pipeline.yaml, prompts/, etc.) into .pilot/
    for src_file in sorted(template_path.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(template_path)
        dst = pilot_dir / rel
        if dst.exists():
            skipped.append(f".pilot/{rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst)
        copied.append(f".pilot/{rel}")

    # Copy built-in agents into .pilot/agents/
    agents_src = get_defaults_dir() / "agents"
    agents_dst = pilot_dir / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    for src_file in sorted(agents_src.glob("*.md")):
        dst = agents_dst / src_file.name
        if dst.exists():
            skipped.append(f".pilot/agents/{src_file.name}")
            continue
        shutil.copy2(src_file, dst)
        copied.append(f".pilot/agents/{src_file.name}")

    # Copy bundled defaults (README.md, protocol.md) into .pilot/
    defaults_dir = get_defaults_dir()
    for name in ("README.md", "protocol.md"):
        src = defaults_dir / name
        dst = pilot_dir / name
        if not src.is_file():
            continue
        if dst.exists():
            skipped.append(f".pilot/{name}")
        else:
            shutil.copy2(src, dst)
            copied.append(f".pilot/{name}")

    # Create .pilot/session/tasks/ and .pilot/session/artifacts/ directories
    session_dir = pilot_dir / "session"
    tasks_dir = session_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    if not list(tasks_dir.iterdir()):
        copied.append(".pilot/session/tasks/")
    artifacts_dir = session_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if copied:
        print(f"Initialized from template '{template_name}':")
        for f in copied:
            print(f"  + {f}")
    if skipped:
        print(f"\nSkipped (already exist):")
        for f in skipped:
            print(f"  ~ {f}")
    if not copied and not skipped:
        print(f"Template '{template_name}' is empty.")

    print(f"\nNext steps:")
    print(f"  1. Add task files to .pilot/session/tasks/")
    print(f"  2. Run: pilot run")


def cmd_agents(args) -> None:
    """List resolved agents for the current project."""
    config_path = args.config or DEFAULT_CONFIG
    config = load_config(config_path)

    agents = config.agents
    if not agents:
        print("No agents configured.")
        return

    print(f"Agents ({len(agents)} loaded):")
    for name in sorted(agents):
        agent = agents[name]
        tool = agent.tool or config.defaults.tool
        model = agent.model or config.defaults.model
        source = agent.source or "unknown"
        # Shorten file paths to just the meaningful part
        if source not in ("pilot.yaml", "unknown"):
            # Show relative-ish path: .pilot/agents/name.md or built-in
            if ".pilot" in source:
                source = ".pilot/agents/" + Path(source).name
            elif "defaults" in source:
                source = "built-in"
        print(f"  {name:<16s}tool={tool:<14s}model={model:<16s}source={source}")


def cmd_doctor(args) -> None:
    """Check environment: Python, config, agents, tasks, tools."""
    checks: list[tuple[str, str, bool]] = []

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    checks.append(("Python", py_ver, py_ok))

    # Config
    config_path = args.config or DEFAULT_CONFIG
    config = None
    if os.path.isfile(config_path):
        try:
            config = load_config(config_path)
            step_count = len(config.pipeline)
            checks.append(("Config", f"{config_path} ({step_count} steps)", True))
        except ConfigError as e:
            checks.append(("Config", f"{config_path} — {e}", False))
    else:
        checks.append(("Config", f"{config_path} not found", False))

    # Agents
    if config:
        checks.append(("Agents", f"{len(config.agents)} loaded", True))
    else:
        checks.append(("Agents", "no config", False))

    # Tasks
    tasks_dir = os.path.join(".pilot", "session", "tasks")
    if os.path.isdir(tasks_dir):
        task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".md")]
        checks.append(("Tasks", f"{len(task_files)} files in .pilot/session/tasks/", True))
    else:
        checks.append(("Tasks", ".pilot/session/tasks/ not found", False))

    # Tool availability
    for label, binary in [("claude-code", "claude")]:
        found = shutil.which(binary) is not None
        checks.append((label, "found" if found else "not found", found))

    # Print results
    print("pilot doctor")
    for label, detail, ok in checks:
        mark = "\u2713" if ok else "\u2717"
        print(f"  {label + ':':<16s}{detail} {mark}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pilot",
        description="PILOT v2 — CLI pipeline orchestrator",
    )
    parser.add_argument("--version", "-V", action="version",
                        version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # pilot run
    run_parser = sub.add_parser("run", help="Execute pipeline")
    run_parser.add_argument("--config", default=DEFAULT_CONFIG)
    run_parser.add_argument("--from", dest="from_step", help="Resume from step ID")
    run_parser.add_argument("--dry-run", action="store_true", help="Show steps without executing")
    run_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    run_parser.add_argument("--debug", nargs="?", const="80", default=None, metavar="CHARS",
                            help="Print state vars before each step (optional: truncate limit, default 80, 0=full)")
    run_parser.add_argument("--branch", default=None, help="Branch name (default: derived from input.md)")
    run_parser.add_argument("--no-branch", action="store_true", help="Disable automatic branch creation")

    # pilot validate
    validate_parser = sub.add_parser("validate", help="Validate pilot.yaml")
    validate_parser.add_argument("--config", default=None)

    # pilot steps
    steps_parser = sub.add_parser("steps", help="List pipeline steps")
    steps_parser.add_argument("--config", default=None)

    # pilot init
    init_parser = sub.add_parser("init", help="Scaffold project from template")
    init_parser.add_argument("template", nargs="?", default="develop",
                             help="Template name (default: develop)")
    init_parser.add_argument("--list", action="store_true", help="List available templates")

    # pilot agents
    agents_parser = sub.add_parser("agents", help="List resolved agents")
    agents_parser.add_argument("--config", default=None)

    # pilot doctor
    doctor_parser = sub.add_parser("doctor", help="Check environment")
    doctor_parser.add_argument("--config", default=None)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "run":
            cmd_run(args)
        elif args.command == "validate":
            cmd_validate(args)
        elif args.command == "steps":
            cmd_steps(args)
        elif args.command == "init":
            cmd_init(args)
        elif args.command == "agents":
            cmd_agents(args)
        elif args.command == "doctor":
            cmd_doctor(args)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)
    except PipelineError as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
