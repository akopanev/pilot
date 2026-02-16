"""Session progress log — timestamped file + colored stdout."""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime


# ── ANSI color constants ────────────────────────────────────

GRAY = "\033[90m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _color_enabled() -> bool:
    """Check whether colored output should be used."""
    if os.environ.get("NO_COLOR") or os.environ.get("PILOT_NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{RESET}"


# Patterns for auto-detecting message color
_COLOR_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"exit_code=(?!0\b)"), RED),        # non-zero exit code
    (re.compile(r"signal:"), BLUE),
    (re.compile(r"✓"), GREEN),
    (re.compile(r"⚠|warning", re.IGNORECASE), YELLOW),
    (re.compile(r"Pipeline started|Pipeline complete"), GREEN),
    (re.compile(r"▸.*\(loop\)"), MAGENTA),
    (re.compile(r"▸.*\(gate\)"), YELLOW),
    (re.compile(r"▸.*\(shell\)"), CYAN),
    (re.compile(r"▸.*\(.+/.+\)"), GREEN),
    (re.compile(r"skipping.*already done"), DIM),
    (re.compile(r"round \d+/\d+"), YELLOW),
    (re.compile(r"emit:"), BLUE),
    (re.compile(r"\[\d+/\d+\]"), MAGENTA),          # loop iteration [1/3]
    (re.compile(r"^\s*🔍|^\s*│"), DIM),              # debug state dump
]


def _detect_color(message: str) -> str | None:
    """Return the ANSI color for a message based on pattern matching."""
    for pattern, color in _COLOR_RULES:
        if pattern.search(message):
            return color
    return None


class ProgressLog:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._file = open(path, "a")
        self._use_color = _color_enabled()

    def section(self, label: str) -> None:
        """Print a section divider: --- label ---

        Ralphex-style section header. Yellow, no timestamp.
        Visually separates pipeline phases from agent streaming output.
        """
        divider = f"--- {label} ---"
        self._file.write(f"\n{divider}\n")
        self._file.flush()

        if self._use_color:
            print(f"\n{colorize(divider, YELLOW)}")
        else:
            print(f"\n{divider}")

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Plain text to file
        plain_line = f"[{timestamp}] {message}\n"
        self._file.write(plain_line)
        self._file.flush()

        # Colored text to terminal
        if self._use_color:
            ts = colorize(f"[{timestamp}]", GRAY)
            color = _detect_color(message)
            msg = colorize(message, color) if color else message
            print(f"{ts} {msg}")
        else:
            print(plain_line, end="")

    def close(self) -> None:
        self._file.close()
