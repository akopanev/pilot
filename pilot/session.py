"""Session state — tracks pipeline progress in .pilot/session.json."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class Session:
    """Persistent session state for a pipeline run.

    Tracks completed top-level steps, current step, branch, and timestamps.
    Iterator loop progress is tracked implicitly via file movement (tasks/ → tasks/completed/).
    Convergence loop state is not persisted (short loops, restart from round 1).
    """

    def __init__(self, config_dir: str):
        self.path = os.path.join(config_dir, "session.json")
        self.branch: str | None = None
        self.started_at: str | None = None
        self.completed: list[str] = []
        self.current: str | None = None
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            return
        with open(self.path) as f:
            data = json.load(f)
        self.branch = data.get("branch")
        self.started_at = data.get("started_at")
        self.completed = data.get("completed", [])
        self.current = data.get("current")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        data = {
            "branch": self.branch,
            "started_at": self.started_at,
            "completed": self.completed,
            "current": self.current,
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def is_done(self, step_id: str) -> bool:
        return step_id in self.completed

    def mark_current(self, step_id: str) -> None:
        self.current = step_id
        self._save()

    def mark_done(self, step_id: str) -> None:
        if step_id not in self.completed:
            self.completed.append(step_id)
        if self.current == step_id:
            self.current = None
        self._save()

    def set_branch(self, branch: str) -> None:
        self.branch = branch
        self._save()

    def start(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._save()
