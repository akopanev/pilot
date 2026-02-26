"""Signal protocol — parse <signal:NAME>content from agent output."""

from __future__ import annotations

import re
from dataclasses import dataclass

# <signal:NAME>content  or  <signal:NAME key=value>content
SIGNAL_RE = re.compile(r"<signal:(\w+)(\s+[^>]*)?>([^<]*)")

BUILTIN_SIGNALS = frozenset({"update", "failed", "var"})


@dataclass
class Signal:
    name: str
    content: str
    attrs: dict[str, str]


def _parse_attrs(raw: str | None) -> dict[str, str]:
    """Parse key=value attributes from signal tag."""
    if not raw:
        return {}
    attrs: dict[str, str] = {}
    for part in raw.strip().split():
        if "=" in part:
            k, _, v = part.partition("=")
            attrs[k.strip()] = v.strip()
    return attrs


def parse_signals(output: str, known_signals: set[str] | None = None) -> list[Signal]:
    """Extract all <signal:NAME>content from output.

    Supports attributes: <signal:var key=NAME>value
    If known_signals is provided, only those + builtins are recognized.
    """
    signals: list[Signal] = []
    allowed = (known_signals | BUILTIN_SIGNALS) if known_signals else None

    for m in SIGNAL_RE.finditer(output):
        name = m.group(1)
        attrs = _parse_attrs(m.group(2))
        content = m.group(3).strip()
        if allowed and name not in allowed:
            continue
        signals.append(Signal(name=name, content=content, attrs=attrs))

    return signals
