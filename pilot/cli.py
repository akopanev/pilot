"""CLI entry point — pilot run / pilot validate / pilot init."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

from pilot import __version__
from pilot.config import ConfigError, load_config
from pilot.display import Display
from pilot.engine import PipelineEngine, PipelineError


def _parse_cli_var(arg: str) -> tuple[str, str]:
    """Parse a `KEY=VALUE` string from --var. Newlines are encoded into
    the vars file as `\\n` literals; multi-line values pass through
    transparently for template substitution and subprocess env."""
    if "=" not in arg:
        raise argparse.ArgumentTypeError(
            f"--var must be KEY=VALUE (got: {arg!r})"
        )
    key, _, value = arg.partition("=")
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError(f"--var key is empty: {arg!r}")
    return key, value


def cmd_run(args) -> None:
    display = Display(verbose=args.verbose)
    display.banner()

    config_path = args.pipeline
    config = load_config(config_path)
    config_dir = os.path.dirname(os.path.abspath(config_path))
    state_path = os.path.join(config_dir, "state")
    vars_path = os.path.join(config_dir, "vars")

    cli_vars: dict[str, str] = dict(args.vars) if args.vars else {}

    if args.dry_run:
        display.info(f"Pipeline: {config_path}")
        display.info(f"Version: {config.version}")
        display.info(f"Start: {config.start_stage}")
        if cli_vars:
            display.info("CLI vars:")
            for k, v in cli_vars.items():
                display.info(f"  [dim]{k}=[/]{v}")
        display.dry_run_stages(config.stages)
        return

    # Open real-time log directory (timestamped subfolder)
    from datetime import datetime
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = os.path.join(config_dir, "logs", run_stamp)
    display.open_log(log_dir)

    display.info(f"[dim]Pipeline:[/] {config_path}")
    display.info(f"[dim]Log:[/]      {log_dir}")
    display.info(f"[dim]State:[/]    {state_path}")
    display.info(f"[dim]Vars:[/]     {vars_path}")
    display.info(f"[dim]Stages:[/]   {', '.join(config.stages.keys())}")

    engine = PipelineEngine(
        config=config,
        config_dir=config_dir,
        state_path=state_path,
        vars_path=vars_path,
        display=display,
        log_dir=log_dir,
        cli_vars=cli_vars,
    )
    try:
        engine.run()
    except KeyboardInterrupt:
        display.warn("Interrupted")
    finally:
        display.close()


def cmd_validate(args) -> None:
    display = Display()
    try:
        config = load_config(args.pipeline)
    except ConfigError as e:
        display.error(str(e))
        sys.exit(1)

    display.console.print(f"[success]Valid[/]: {len(config.stages)} stages")


def cmd_graph(args) -> None:
    """Generate pipeline graph as PNG."""
    from pilot.graph import build_graph, open_file
    display = Display()
    try:
        output = build_graph(args.pipeline, args.output)
    except ConfigError as e:
        display.error(str(e))
        sys.exit(1)
    display.console.print(f"[success]Graph saved:[/] {output}")
    if not args.no_open:
        open_file(output)


def _discover_pipelines(defaults_dir: Path) -> dict[str, str]:
    """Return {pipeline_name: description} for every dir with a pipeline.yaml.

    Description = first non-empty comment line of pipeline.yaml,
    fallback to the directory name.
    """
    out: dict[str, str] = {}
    for d in sorted(defaults_dir.iterdir()):
        if not d.is_dir() or not (d / "pipeline.yaml").is_file():
            continue
        desc = d.name
        with open(d / "pipeline.yaml") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    desc = stripped.lstrip("#").strip() or d.name
                break
        out[d.name] = desc
    return out


def cmd_init(args) -> None:
    """Scaffold .pilot/ with selected pipelines."""
    display = Display()
    defaults_dir = Path(__file__).parent / "defaults"

    if not defaults_dir.is_dir():
        display.error("Default pipelines not found in package.")
        sys.exit(1)

    available = _discover_pipelines(defaults_dir)
    if not available:
        display.error("No pipelines found in defaults.")
        sys.exit(1)

    # No args, no --all: list and exit
    if not args.pipelines and not args.all:
        display.console.print("[bold]Available pipelines:[/]\n")
        name_w = max(len(n) for n in available)
        for name, desc in available.items():
            display.console.print(f"  [stage]{name:<{name_w}}[/]  [dim]{desc}[/]")
        display.console.print()
        display.console.print("[dim]Usage:[/]")
        display.console.print("  pilot init <name> [<name>...]   install selected pipelines")
        display.console.print("  pilot init --all                install everything")
        return

    # Resolve selection
    if args.all:
        selected = list(available.keys())
    else:
        unknown = [n for n in args.pipelines if n not in available]
        if unknown:
            display.error(
                f"Unknown pipeline(s): {', '.join(unknown)}. "
                f"Available: {', '.join(available)}"
            )
            sys.exit(1)
        # Preserve user-specified order; dedupe
        seen: set[str] = set()
        selected = []
        for n in args.pipelines:
            if n not in seen:
                selected.append(n)
                seen.add(n)

    pilot_dir = Path.cwd() / ".pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)

    # Plan: per-pipeline files + shared scripts/ (always included)
    plan: list[tuple[Path, Path]] = []  # (src, dst)
    seen_dst: set[Path] = set()
    for name in selected:
        for src in sorted((defaults_dir / name).rglob("*")):
            if not src.is_file():
                continue
            dst = pilot_dir / src.relative_to(defaults_dir)
            if dst not in seen_dst:
                plan.append((src, dst))
                seen_dst.add(dst)
    shared_scripts = defaults_dir / "scripts"
    if shared_scripts.is_dir():
        for src in sorted(shared_scripts.rglob("*")):
            if not src.is_file():
                continue
            dst = pilot_dir / src.relative_to(defaults_dir)
            if dst not in seen_dst:
                plan.append((src, dst))
                seen_dst.add(dst)

    conflicts = [dst for _, dst in plan if dst.exists()]

    overwrite_all = args.force
    if conflicts and not overwrite_all:
        display.console.print("[yellow]Existing files will be overwritten:[/]")
        for c in conflicts:
            display.console.print(f"  [yellow]~[/] {c.relative_to(pilot_dir)}")
        if not sys.stdin.isatty():
            display.console.print(
                "[dim]Non-interactive shell — use --force to overwrite. "
                "Skipping conflicts.[/]"
            )
        else:
            try:
                answer = input("\nOverwrite? [y/N]: ").strip().lower()
            except EOFError:
                answer = ""
            if answer in ("y", "yes"):
                overwrite_all = True
            else:
                display.console.print("[dim]Keeping existing files.[/]")

    copied: list[str] = []
    skipped: list[str] = []
    for src, dst in plan:
        rel = str(src.relative_to(defaults_dir))
        if dst.exists() and not overwrite_all:
            skipped.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)

    if copied:
        display.console.print("[success]Initialized .pilot/[/]")
        for f in copied:
            display.console.print(f"  [green]+[/] {f}")
    if skipped:
        display.console.print("[yellow]Skipped[/] (existing):")
        for f in skipped:
            display.console.print(f"  [dim]~[/] {f}")
    if not copied and not skipped:
        display.console.print("[dim].pilot/ already fully initialized.[/]")

    display.console.print(
        f"\n[dim]Next:[/] pilot run .pilot/{selected[0]}/pipeline.yaml"
    )


def _read_skill_field(pipeline_yaml_path: Path) -> str | None:
    """Return the top-level `skill:` string from a pipeline.yaml, or None.

    Used by `pilot init-skill` to materialise a Claude Code skill from
    the pipeline's bundled SKILL.md template.
    """
    import yaml
    try:
        with open(pipeline_yaml_path) as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, dict):
        return None
    skill = raw.get("skill")
    if isinstance(skill, str) and skill.strip():
        return skill
    return None


def cmd_init_skill(args) -> None:
    """Install a pipeline's bundled SKILL.md template into .claude/skills/<name>/.

    Reads the top-level `skill:` field from `.pilot/<name>/pipeline.yaml`
    and writes it verbatim to `.claude/skills/<name>/SKILL.md`. The
    pipeline author owns the SKILL.md content; pilot just copies.
    """
    display = Display()
    cwd = Path.cwd()
    pilot_dir = cwd / ".pilot"

    # No args: list pipelines that have a skill template
    if not args.name:
        display.console.print("[bold]Pipelines with a skill template:[/]\n")
        if not pilot_dir.is_dir():
            display.console.print(
                "  [dim](no .pilot/ directory in this project — run "
                "`pilot init <name>` first)[/]"
            )
            return
        any_listed = False
        for sub in sorted(pilot_dir.iterdir()):
            if not sub.is_dir():
                continue
            yaml_path = sub / "pipeline.yaml"
            if not yaml_path.is_file():
                continue
            has_skill = _read_skill_field(yaml_path) is not None
            marker = "[green]✓[/]" if has_skill else "[dim]·[/]"
            note = "" if has_skill else "[dim] (no skill: block)[/]"
            display.console.print(f"  {marker} [stage]{sub.name}[/]{note}")
            any_listed = True
        if not any_listed:
            display.console.print("  [dim](no pipelines installed — run `pilot init <name>` first)[/]")
        display.console.print()
        display.console.print("[dim]Usage:[/]  pilot init-skill <name>")
        return

    name = args.name
    pipeline_yaml = pilot_dir / name / "pipeline.yaml"
    if not pipeline_yaml.is_file():
        display.error(
            f"No pipeline at .pilot/{name}/pipeline.yaml — "
            f"run `pilot init {name}` first."
        )
        sys.exit(1)

    skill_content = _read_skill_field(pipeline_yaml)
    if skill_content is None:
        display.error(
            f"Pipeline `{name}` has no `skill:` block in "
            f".pilot/{name}/pipeline.yaml — add a top-level `skill: |` "
            f"string carrying the SKILL.md content first."
        )
        sys.exit(1)

    skill_dir = cwd / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"

    if skill_md.exists() and not args.force:
        display.error(
            f".claude/skills/{name}/SKILL.md already exists — pass --force "
            f"to overwrite."
        )
        sys.exit(1)

    skill_md.write_text(skill_content)

    display.console.print(
        f"[success]Installed skill[/] [stage]{name}[/]"
    )
    display.console.print(f"  [green]+[/] .claude/skills/{name}/SKILL.md")
    display.console.print(
        f"\n[dim]Use it in Claude Code:[/]  /{name} \"<your question>\""
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pilot",
        description="PILOT -- config-driven pipeline engine for AI agents",
    )
    parser.add_argument("--version", "-V", action="version",
                        version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # pilot run <pipeline.yaml>
    run_p = sub.add_parser("run", help="Execute pipeline")
    run_p.add_argument("pipeline", help="Path to pipeline yaml")
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--verbose", action="store_true")
    run_p.add_argument(
        "--var", action="append", dest="vars", default=[],
        type=_parse_cli_var, metavar="KEY=VALUE",
        help="Set a pipeline var. Repeatable. CLI vars take precedence "
             "over `vars:` declared in the pipeline yaml.",
    )

    # pilot validate <pipeline.yaml>
    val_p = sub.add_parser("validate", help="Validate pipeline yaml")
    val_p.add_argument("pipeline", help="Path to pipeline yaml")

    # pilot graph <pipeline.yaml>
    graph_p = sub.add_parser("graph", help="Generate pipeline graph as PNG")
    graph_p.add_argument("pipeline", help="Path to pipeline yaml")
    graph_p.add_argument("-o", "--output", help="Output file path (without extension)")
    graph_p.add_argument("--no-open", action="store_true", help="Don't open the image")

    # pilot init [pipeline ...] [--all] [--force]
    init_p = sub.add_parser("init", help="Scaffold .pilot/ with selected pipelines")
    init_p.add_argument("pipelines", nargs="*",
                        help="Pipeline names to install (omit to list available)")
    init_p.add_argument("--all", action="store_true",
                        help="Install all available pipelines")
    init_p.add_argument("--force", action="store_true",
                        help="Overwrite existing files without confirmation")

    # pilot init-skill [name] [--force]
    skill_p = sub.add_parser(
        "init-skill",
        help="Install a pipeline's SKILL.md template into .claude/skills/",
    )
    skill_p.add_argument("name", nargs="?",
                         help="Pipeline name (omit to list pipelines with skill templates)")
    skill_p.add_argument("--force", action="store_true",
                         help="Overwrite existing .claude/skills/<name>/SKILL.md")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        {
            "run": cmd_run,
            "validate": cmd_validate,
            "init": cmd_init,
            "init-skill": cmd_init_skill,
            "graph": cmd_graph,
        }[args.command](args)
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
