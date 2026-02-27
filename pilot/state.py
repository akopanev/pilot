"""Pipeline state persistence — .pilot/state file."""

from __future__ import annotations

import os

from pilot.models import PipelineState


def read_state(path: str) -> PipelineState | None:
    """Read state from file. Returns None if file doesn't exist.

    Format: stage round
    Example: review 7
    """
    if not os.path.isfile(path):
        return None

    with open(path) as f:
        line = f.read().strip()

    if not line:
        return None

    parts = line.split()
    if len(parts) != 2:
        return None

    stage = parts[0]
    try:
        round_num = int(parts[1])
    except ValueError:
        return None

    return PipelineState(stage=stage, round=round_num)


def write_state(path: str, state: PipelineState) -> None:
    """Write state to file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(f"{state.stage} {state.round}\n")


def clear_state(path: str) -> None:
    """Remove state file."""
    if os.path.isfile(path):
        os.remove(path)
