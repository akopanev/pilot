"""Rich terminal output — banners, round headers, signals, transitions."""

from __future__ import annotations

import os
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

from pilot import __version__

PILOT_THEME = Theme({
    "stage": "bold cyan",
    "signal": "bold blue",
    "signal.update": "dim",
    "signal.failed": "bold red",
    "signal.domain": "bold green",
    "transition": "bold yellow",
    "runner": "dim",
    "timestamp": "dim",
    "error": "bold red",
    "success": "bold green",
    "round": "bold magenta",
})


class Display:
    """Formatted terminal output for the pipeline engine."""

    def __init__(self, no_color: bool = False, verbose: bool = False):
        force_terminal = None
        if no_color or os.environ.get("NO_COLOR") or os.environ.get("PILOT_NO_COLOR"):
            force_terminal = False
        self.console = Console(
            theme=PILOT_THEME,
            force_terminal=force_terminal,
            stderr=False,
        )
        self.verbose = verbose

    def banner(self) -> None:
        """Startup banner."""
        title = Text.assemble(
            ("PILOT", "bold white"),
            (" v", "dim"),
            (__version__, "dim"),
        )
        self.console.print(Panel(
            title,
            border_style="cyan",
            padding=(0, 2),
        ))

    def round_header(self, round_num: int, stage_name: str,
                     executor: str, model: str | None) -> None:
        """Round divider with stage and runner info."""
        runner_label = f"({executor} / {model})" if model else f"({executor})"
        label = Text.assemble(
            (f" Round {round_num} ", "round"),
            ("| ", "dim"),
            (stage_name, "stage"),
            ("  ", ""),
            (runner_label, "runner"),
        )
        self.console.print()
        self.console.print(Rule(label, style="dim"))

    def update(self, content: str) -> None:
        """Display an update signal."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [signal.update]{content}[/]")

    def domain_signal(self, name: str, content: str) -> None:
        """Display a domain signal (approved, rejected, etc.)."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [signal.domain]<signal:{name}>[/] {content}")

    def transition(self, from_stage: str, to_stage: str) -> None:
        """Display stage transition."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [dim]{from_stage}[/] [transition]->[/] [stage]{to_stage}[/]")

    def error(self, message: str) -> None:
        """Display error."""
        self.console.print(Panel(
            message,
            title="[error]Error[/]",
            border_style="red",
            padding=(0, 1),
        ))

    def done(self, summary: str = "complete") -> None:
        """Display pipeline completion."""
        self.console.print()
        self.console.print(Panel(
            summary,
            title="[success]Done[/]",
            border_style="green",
            padding=(0, 1),
        ))

    def info(self, message: str) -> None:
        """Display info line."""
        ts = self._timestamp()
        self.console.print(f"  {ts} {message}")

    def warn(self, message: str) -> None:
        """Display warning."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [yellow]{message}[/]")

    def fallback(self, primary: str, fallback: str) -> None:
        """Display fallback runner activation."""
        ts = self._timestamp()
        self.console.print(
            f"  {ts} [yellow]Fallback:[/] {primary} [dim]->[/] {fallback}"
        )

    def executor_output(self, line: str) -> None:
        """Stream executor output line."""
        if self.verbose:
            self.console.print(f"    [dim]{line.rstrip()}[/]")

    def _timestamp(self) -> str:
        now = datetime.now().strftime("%H:%M:%S")
        return f"[timestamp]{now}[/]"

    def dry_run_stages(self, stages: dict) -> None:
        """Display pipeline stages in dry-run mode."""
        self.console.print("\n[bold]Pipeline stages:[/]\n")
        for name, stage in stages.items():
            runner_info = f"{stage.runner.executor}/{stage.runner.model}" if stage.runner.model else stage.runner.executor
            fallback = ""
            if stage.fallback_runner:
                fallback = f" [dim](fallback: {stage.fallback_runner.executor}/{stage.fallback_runner.model})[/]"

            self.console.print(f"  [stage]{name}[/]  [runner]{runner_info}[/]{fallback}")

            for sig_name, trans in stage.on_signal.items():
                dest = trans.to or "[dim]stop[/]"
                marker = "[dim]default[/]" if sig_name == "default" else f"[signal.domain]{sig_name}[/]"
                self.console.print(f"    {marker} -> {dest}")

            self.console.print()
