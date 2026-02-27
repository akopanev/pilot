"""Rich terminal output — banners, round headers, signals, transitions."""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

from pilot import __version__

# Strip Rich markup for plain-text log
_MARKUP_RE = re.compile(r"\[/?[^\]]*\]")

PILOT_THEME = Theme({
    "stage": "bold cyan",
    "signal.update": "dim",
    "signal.failed": "bold red",
    "signal.domain": "bold",
    "runner": "dim",
    "timestamp": "dim",
    "error": "bold red",
    "success": "bold green",
    "round": "bold",
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
        self._log_file = None

    def open_log(self, path: str) -> None:
        """Open a log file for plain-text mirroring."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._log_file = open(path, "a")

    def _log(self, message: str) -> None:
        """Write a plain-text line to the log file."""
        if not self._log_file:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        plain = _MARKUP_RE.sub("", message)
        self._log_file.write(f"[{ts}] {plain}\n")
        self._log_file.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._log_file:
            self._log_file.close()
            self._log_file = None

    def banner(self) -> None:
        """Startup banner."""
        title = Text.assemble(
            ("PILOT", "bold white"),
            (" v", "dim"),
            (__version__, "dim"),
        )
        self.console.print(Panel(
            title,
            border_style="dim",
            padding=(0, 2),
        ))

    def round_header(self, round_num: int, stage_name: str,
                     executor: str, model: str | None) -> None:
        """Round divider with stage and runner info."""
        runner_label = f"({executor} / {model})" if model else f"({executor})"
        # Build left-aligned header: ─── Round N | stage  (runner) ────────
        title = f"Round {round_num} | {stage_name}  {runner_label}"
        width = self.console.width or 80
        pad = max(4, width - len(title) - 5)  # 5 = "─── " + " "
        line = Text.assemble(
            ("─── ", "dim"),
            (f"Round {round_num} ", "round"),
            ("| ", "dim"),
            (stage_name, "stage"),
            ("  ", ""),
            (runner_label, "runner"),
            (" ", ""),
            ("─" * pad, "dim"),
        )
        self.console.print()
        self.console.print(line)
        self._log(f"--- Round {round_num} | {stage_name}  {runner_label} ---")

    def update(self, content: str) -> None:
        """Display an update signal."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [signal.update]{content}[/]", highlight=False)
        self._log(content)

    def domain_signal(self, name: str, content: str) -> None:
        """Display a domain signal (approved, rejected, etc.)."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [signal.domain]{name}:[/] {content}", highlight=False)
        self._log(f"<signal:{name}> {content}")

    def transition(self, from_stage: str, to_stage: str) -> None:
        """Display stage transition."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [dim]{from_stage} ->[/] [stage]{to_stage}[/]")
        self._log(f"{from_stage} -> {to_stage}")

    def error(self, message: str) -> None:
        """Display error."""
        self.console.print(Panel(
            message,
            title="[error]Error[/]",
            border_style="red",
            padding=(0, 1),
        ))
        self._log(f"ERROR: {message}")

    def done(self, summary: str = "complete") -> None:
        """Display pipeline completion."""
        self.console.print()
        self.console.print(Panel(
            summary,
            title="[success]Done[/]",
            border_style="green",
            padding=(0, 1),
        ))
        self._log(f"DONE: {summary}")

    def info(self, message: str) -> None:
        """Display info line."""
        ts = self._timestamp()
        self.console.print(f"  {ts} {message}", highlight=False)
        self._log(message)

    def warn(self, message: str) -> None:
        """Display warning."""
        ts = self._timestamp()
        self.console.print(f"  {ts} [yellow]{message}[/]")
        self._log(f"WARN: {message}")

    def fallback(self, primary: str, fallback: str) -> None:
        """Display fallback runner activation."""
        ts = self._timestamp()
        self.console.print(
            f"  {ts} [yellow]Fallback:[/] {primary} [dim]->[/] {fallback}"
        )
        self._log(f"Fallback: {primary} -> {fallback}")

    def executor_output(self, text: str) -> None:
        """Stream executor output — always logged, terminal only in verbose."""
        stripped = text.rstrip()
        if not stripped:
            return
        if self.verbose:
            self.console.print(f"    [dim]{stripped}[/]")
        self._log(stripped)

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
