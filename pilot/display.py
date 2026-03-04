"""Rich terminal output — banners, round headers, signals, transitions."""

from __future__ import annotations

import os
import re
import sys
import threading
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
        self._log_dir = None
        self._round_file = None
        self._lock = threading.Lock()

    def open_log(self, log_dir: str) -> None:
        """Open log directory for per-round logs."""
        os.makedirs(log_dir, exist_ok=True)
        self._log_dir = log_dir

    def _log(self, message: str) -> None:
        """Write a plain-text line to current round log (thread-safe)."""
        with self._lock:
            if not self._round_file:
                return
            ts = datetime.now().strftime("%H:%M:%S")
            plain = _MARKUP_RE.sub("", message)
            self._round_file.write(f"[{ts}] {plain}\n")
            self._round_file.flush()

    def close(self) -> None:
        """Close log files."""
        with self._lock:
            if self._round_file:
                self._round_file.close()
                self._round_file = None

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
        # Open per-round log file
        if self._log_dir:
            with self._lock:
                if self._round_file:
                    self._round_file.close()
                slug = f"{executor}-{model}" if model else executor
                slug = slug.replace("/", "-")
                filename = f"{round_num:03d}-{stage_name}-{slug}.txt"
                self._round_file = open(os.path.join(self._log_dir, filename), "w")

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
        self.console.print(f"  {ts} [dim]{from_stage} ->[/] [stage]{to_stage}[/]", highlight=False)
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

    def done(self, summary: str = "complete", stats: str = "") -> None:
        """Display pipeline completion."""
        self.console.print()
        body = summary
        if stats:
            body = f"{summary} [dim]({stats})[/]"
        self.console.print(Panel(
            body,
            title="[success]Done[/]",
            border_style="green",
            padding=(0, 1),
        ))
        plain = f"{summary} ({stats})" if stats else summary
        self._log(f"DONE: {plain}")

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
