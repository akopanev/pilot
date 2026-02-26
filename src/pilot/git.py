"""Git utilities for branch management."""

from __future__ import annotations

import subprocess


def get_default_branch() -> str:
    """Detect default branch from git repo."""
    # Try remote HEAD
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            remote_default = result.stdout.strip().split("/")[-1]
            verify = subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/heads/{remote_default}"],
                capture_output=True, text=True,
            )
            if verify.returncode == 0:
                return remote_default
    except Exception:
        pass

    for branch in ["main", "master", "trunk", "develop"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return branch

    return "main"


def get_current_branch() -> str | None:
    """Get current branch name, or None if detached HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        branch = result.stdout.strip()
        return None if branch == "HEAD" else branch
    return None
