"""Git utilities for branch management and diff commands."""

from __future__ import annotations

import re
import subprocess
import time


def get_default_branch() -> str:
    """Detect default branch from git repo.

    Checks origin/HEAD first, then falls back to common branch names.
    """
    # Try remote HEAD (but verify the LOCAL branch exists)
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

    # Try common names — prefer branches that have a matching remote
    for branch in ["main", "master", "trunk", "develop"]:
        local = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            capture_output=True, text=True,
        )
        remote = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"],
            capture_output=True, text=True,
        )
        if local.returncode == 0 and remote.returncode == 0:
            return branch

    # Fallback: any local branch with a common name
    for branch in ["main", "master", "trunk", "develop"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return branch

    return "master"


def get_head_hash() -> str:
    """Get current HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


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


def is_on_default_branch() -> bool:
    """Check if currently on the default branch."""
    current = get_current_branch()
    if not current:
        return False
    default = get_default_branch()
    return current == default


def derive_branch_name(input_path: str) -> str:
    """Derive branch name from input.md first non-empty line.

    Reads the first meaningful line, slugifies it, and returns pilot/{slug}.
    Falls back to pilot/run-{timestamp} if nothing useful found.
    """
    try:
        with open(input_path) as f:
            for line in f:
                line = line.strip().lstrip("#").strip()
                if line and not line.startswith("<!--"):
                    slug = re.sub(r"[^a-z0-9]+", "-", line.lower()).strip("-")[:50]
                    if slug:
                        return f"pilot/{slug}"
    except FileNotFoundError:
        pass
    return f"pilot/run-{int(time.time())}"


def create_branch(branch_name: str) -> tuple[bool, str]:
    """Create and checkout a new branch. Returns (success, error_message)."""
    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True, text=True,
    )
    error = result.stderr.strip() if result.returncode != 0 else ""
    return result.returncode == 0, error


def get_diff_command(default_branch: str, **_kwargs) -> str:
    """Return git diff command showing all branch changes.

    Always diffs against the default branch so the reviewer sees the
    complete picture — implement commits and fix amends both land on HEAD.
    """
    return f"git diff {default_branch}...HEAD"
