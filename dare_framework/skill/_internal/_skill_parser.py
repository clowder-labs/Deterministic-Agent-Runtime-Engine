"""Parse SKILL.md format (YAML frontmatter + markdown body)."""

from __future__ import annotations

import re
from typing import Any


def parse_skill_md(content: str) -> tuple[dict[str, Any], str]:
    """Parse SKILL.md: extract frontmatter dict and body content.

    Args:
        content: Raw file content.

    Returns:
        (frontmatter_dict, body_text)
    """
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if not fm_match:
        return {}, content.strip()

    fm_text, body = fm_match.group(1).strip(), fm_match.group(2).strip()
    frontmatter = _parse_frontmatter(fm_text)
    return frontmatter, body


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Simple YAML-like frontmatter parser for common fields."""
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # Unquote if needed
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1].replace('\\"', '"')
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1].replace("\\'", "'")
            result[key] = val
    return result


__all__ = ["parse_skill_md"]
