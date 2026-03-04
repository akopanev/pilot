"""Pipeline vars — persistent key=value pairs across rounds."""

from __future__ import annotations

import os


def read_vars(path: str) -> dict[str, str]:
    """Read vars from file. Returns empty dict if file doesn't exist.

    Format: KEY=VALUE (one per line, # comments, blank lines ignored).
    """
    if not os.path.isfile(path):
        return {}

    result: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()

    return result


def write_var(path: str, key: str, value: str) -> None:
    """Set a single var. Updates existing key or appends new one."""
    lines: list[str] = []
    found = False

    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _, _ = stripped.partition("=")
                    if k.strip() == key:
                        lines.append(f"{key}={value}\n")
                        found = True
                        continue
                lines.append(line)

    if not found:
        lines.append(f"{key}={value}\n")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.writelines(lines)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def export_vars(path: str) -> None:
    """Load vars into os.environ."""
    for key, value in read_vars(path).items():
        os.environ[key] = value


def clear_vars(path: str) -> None:
    """Remove vars file."""
    if os.path.isfile(path):
        os.remove(path)
