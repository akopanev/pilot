"""Pipeline vars — persistent key=value pairs across rounds.

The vars file is line-based: one `KEY=VALUE` per line. To allow values
to contain literal newlines (e.g. multi-line prompts passed via --var),
values are encoded on write and decoded on read:

    \\        →   \\\\
    newline   →   \\n

Each var stays on a single line. Existing single-line values without
backslashes round-trip unchanged.
"""

from __future__ import annotations

import os


def _encode(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _decode(value: str) -> str:
    """Reverse `_encode`. Walks the string once to handle `\\\\` and `\\n`
    correctly without misinterpreting `\\\\n` (an encoded backslash
    followed by a literal n) as an encoded newline."""
    out: list[str] = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def read_vars(path: str) -> dict[str, str]:
    """Read vars from file. Returns empty dict if file doesn't exist.

    Format: KEY=VALUE (one per line, # comments, blank lines ignored).
    Values are decoded so encoded newlines (`\\n`) become real newlines.
    """
    if not os.path.isfile(path):
        return {}

    result: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                result[key.strip()] = _decode(value)

    return result


def write_var(path: str, key: str, value: str) -> None:
    """Set a single var. Updates existing key or appends new one.

    Values containing newlines or backslashes are encoded so each var
    occupies exactly one line in the file.
    """
    encoded = _encode(value)
    lines: list[str] = []
    found = False

    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _, _ = stripped.partition("=")
                    if k.strip() == key:
                        lines.append(f"{key}={encoded}\n")
                        found = True
                        continue
                lines.append(line)

    if not found:
        lines.append(f"{key}={encoded}\n")

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
