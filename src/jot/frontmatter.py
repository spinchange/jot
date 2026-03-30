"""Parse and write YAML frontmatter in markdown files."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FENCE_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown string into (frontmatter_dict, body).

    Returns ({}, text) if no valid frontmatter block is present.
    Unknown fields are preserved as-is.
    """
    m = _FENCE_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    body = text[m.end():]
    return data, body


class _IndentedDumper(yaml.Dumper):
    """YAML dumper that indents list items under their key."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow=flow, indentless=False)


def dump(frontmatter: dict[str, Any], body: str) -> str:
    """Combine frontmatter dict and body back into a markdown string."""
    if not frontmatter:
        return body
    fm_text = yaml.dump(
        frontmatter,
        Dumper=_IndentedDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip("\n")
    return f"---\n{fm_text}\n---\n{body}"
