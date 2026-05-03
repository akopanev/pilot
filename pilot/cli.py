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


def cmd_run(args) -> None:
    display = Display(verbose=args.verbose)
    display.banner()

    config_path = args.pipeline
    config = load_config(config_path)
    config_dir = os.path.dirname(os.path.abspath(config_path))
    state_path = os.path.join(config_dir, "state")
    vars_path = os.path.join(config_dir, "vars")

    if args.dry_run:
        display.info(f"Pipeline: {config_path}")
        display.info(f"Version: {config.version}")
        display.info(f"Start: {config.start_stage}")
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        {"run": cmd_run, "validate": cmd_validate, "init": cmd_init, "graph": cmd_graph}[args.command](args)
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
