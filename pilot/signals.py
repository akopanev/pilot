"""XML signal parsing from model output."""

from __future__ import annotations

import re
from dataclasses import dataclass


SIGNAL_PATTERNS = {
    "approve":    re.compile(r"<pilot:approve\s*/>"),
    "reject":     re.compile(r"<pilot:reject>(.*?)</pilot:reject>", re.DOTALL),
    "blocked":    re.compile(r"<pilot:blocked>(.*?)</pilot:blocked>", re.DOTALL),
    "question":   re.compile(r"<pilot:question>(.*?)</pilot:question>", re.DOTALL),
    "update":     re.compile(r'<pilot:update\s+path="([^"]+)">(.*?)</pilot:update>', re.DOTALL),
    "draft":      re.compile(r'<pilot:draft\s+label="([^"]+)">(.*?)</pilot:draft>', re.DOTALL),
    "completed":  re.compile(r"<pilot:completed\s*/>|<pilot:completed>(.*?)</pilot:completed>", re.DOTALL),
    "skip":       re.compile(r"<pilot:skip\s*/>|<pilot:skip>(.*?)</pilot:skip>", re.DOTALL),
    "emit":       re.compile(r'<pilot:emit\s+key="([^"]+)">(.*?)</pilot:emit>', re.DOTALL),
}


@dataclass
class Signal:
    type: str                     # approve, reject, blocked, question, update, draft, completed, skip, emit
    payload: str | None = None    # text content (findings, reason, summary, etc.)
    path: str | None = None       # for update signals
    label: str | None = None      # for draft signals
    key: str | None = None        # for emit signals


def parse_signals(output: str) -> list[Signal]:
    """Extract all pilot:* signals from model output."""
    signals: list[Signal] = []

    if SIGNAL_PATTERNS["approve"].search(output):
        signals.append(Signal(type="approve"))

    for m in SIGNAL_PATTERNS["reject"].finditer(output):
        signals.append(Signal(type="reject", payload=m.group(1).strip()))

    for m in SIGNAL_PATTERNS["blocked"].finditer(output):
        signals.append(Signal(type="blocked", payload=m.group(1).strip()))

    for m in SIGNAL_PATTERNS["question"].finditer(output):
        signals.append(Signal(type="question", payload=m.group(1).strip()))

    for m in SIGNAL_PATTERNS["update"].finditer(output):
        signals.append(Signal(type="update", path=m.group(1), payload=m.group(2)))

    for m in SIGNAL_PATTERNS["draft"].finditer(output):
        signals.append(Signal(type="draft", label=m.group(1), payload=m.group(2)))

    for m in SIGNAL_PATTERNS["completed"].finditer(output):
        payload = (m.group(1) or "").strip() or None
        signals.append(Signal(type="completed", payload=payload))

    for m in SIGNAL_PATTERNS["skip"].finditer(output):
        payload = (m.group(1) or "").strip() or None
        signals.append(Signal(type="skip", payload=payload))

    for m in SIGNAL_PATTERNS["emit"].finditer(output):
        signals.append(Signal(type="emit", key=m.group(1), payload=m.group(2).strip()))

    return signals
