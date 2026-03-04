"""Signal protocol — parse <signal:NAME>content from agent output."""

from __future__ import annotations

import re
from dataclasses import dataclass

# <signal:NAME>content  or  <signal:NAME key=value>content
SIGNAL_RE = re.compile(r"<signal:(\w+)(\s+[^>]*)?>([^<]*)")

BUILTIN_SIGNALS = frozenset({"update", "var"})


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


# Complete signal with closing tag: <signal:NAME>content</signal:NAME>
_COMPLETE_RE = re.compile(r"<signal:(\w+)(\s+[^>]*)?>([^<]*)</signal:\1>")


class SignalScanner:
    """Buffered signal parser for streaming text chunks.

    Handles signals split across chunk boundaries by buffering
    incomplete <signal:NAME>...</signal:NAME> tags.
    """

    def __init__(self, known_signals: set[str] | None = None):
        self._partial = ""
        self._known = known_signals

    def feed(self, text: str) -> list[Signal]:
        """Feed a text chunk. Returns complete signals found."""
        text = self._partial + text
        self._partial = ""

        allowed = (self._known | BUILTIN_SIGNALS) if self._known else None
        signals: list[Signal] = []
        last_end = 0

        for m in _COMPLETE_RE.finditer(text):
            name = m.group(1)
            last_end = m.end()
            if allowed and name not in allowed:
                continue
            signals.append(Signal(
                name=name,
                content=m.group(3).strip(),
                attrs=_parse_attrs(m.group(2)),
            ))

        # Buffer trailing incomplete signal tag
        remaining = text[last_end:]
        tag_start = remaining.find("<signal:")
        if tag_start >= 0:
            self._partial = remaining[tag_start:]

        return signals

    def flush(self) -> list[Signal]:
        """Parse remaining buffer (tolerates missing close tag)."""
        if self._partial:
            signals = parse_signals(self._partial, self._known)
            self._partial = ""
            return signals
        return []
