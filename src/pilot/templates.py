"""Prompt template resolution — {{file:path}} and {{var:NAME}} placeholders."""

from __future__ import annotations

import os
import re

from pilot.vars import read_vars

FILE_RE = re.compile(r"\{\{file:([^}]+)\}\}")
VAR_RE = re.compile(r"\{\{var:([^}]+)\}\}")

MAX_DEPTH = 10


class TemplateError(Exception):
    pass


def resolve_templates(
    content: str,
    base_dir: str,
    vars_path: str | None = None,
    _depth: int = 0,
) -> str:
    """Replace {{file:path}} and {{var:NAME}} with resolved values.

    {{file:path}} — inline file contents (relative to base_dir, recursive).
    {{var:NAME}}  — inline var value from vars file.
    """
    if _depth > MAX_DEPTH:
        raise TemplateError(f"Template recursion depth exceeded ({MAX_DEPTH})")

    def _replace_file(m: re.Match) -> str:
        rel_path = m.group(1).strip()
        abs_path = os.path.join(base_dir, rel_path)

        if not os.path.isfile(abs_path):
            raise TemplateError(f"Template file not found: {rel_path} (looked at {abs_path})")

        with open(abs_path) as f:
            file_content = f.read()

        return resolve_templates(file_content, base_dir, vars_path, _depth + 1)

    result = FILE_RE.sub(_replace_file, content)

    # Resolve vars (no recursion needed — vars are plain values)
    if vars_path:
        vars_dict = read_vars(vars_path)

        def _replace_var(m: re.Match) -> str:
            name = m.group(1).strip()
            if name not in vars_dict:
                raise TemplateError(f"Var not found: {name}")
            return vars_dict[name]

        result = VAR_RE.sub(_replace_var, result)

    return result
