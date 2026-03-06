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


def cmd_init(args) -> None:
    """Copy all default pipelines into .pilot/ in the current directory."""
    display = Display()
    defaults_dir = Path(__file__).parent / "defaults"

    if not defaults_dir.is_dir():
        display.error("Default pipelines not found in package.")
        sys.exit(1)

    pilot_dir = Path.cwd() / ".pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    skipped = []

    for src in sorted(defaults_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(defaults_dir)
        dst = pilot_dir / rel
        if dst.exists():
            skipped.append(str(rel))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))

    if copied:
        display.console.print("[success]Initialized .pilot/[/]")
        for f in copied:
            display.console.print(f"  [green]+[/] {f}")
    if skipped:
        display.console.print("[yellow]Skipped[/] (already exist):")
        for f in skipped:
            display.console.print(f"  [dim]~[/] {f}")
    if not copied and not skipped:
        display.console.print("[dim].pilot/ already fully initialized.[/]")

    display.console.print(f"\n[dim]Next:[/] pilot run .pilot/dev/pipeline.yaml")


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

    # pilot init
    sub.add_parser("init", help="Scaffold .pilot/ with default dev pipeline")

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
