"""Pipeline state persistence — .pilot/state file."""

from __future__ import annotations

import os

from pilot.models import PipelineState


def read_state(path: str) -> PipelineState | None:
    """Read state from file. Returns None if file doesn't exist.

    Format: stage
    Example: review
    """
    if not os.path.isfile(path):
        return None

    with open(path) as f:
        line = f.read().strip()

    if not line:
        return None

    return PipelineState(stage=line.split()[0])


def write_state(path: str, state: PipelineState) -> None:
    """Write state to file (atomic via rename)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(f"{state.stage}\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def clear_state(path: str) -> None:
    """Remove state file."""
    if os.path.isfile(path):
        os.remove(path)
