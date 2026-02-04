"""Skill domain types (Claude Code / Agent Skills format)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    """Parsed skill definition from SKILL.md (Agent Skills format).

    Each skill is a folder containing SKILL.md with YAML frontmatter + markdown body,
    and optionally a scripts/ directory with executable scripts.
    """

    id: str
    name: str
    description: str
    content: str
    skill_dir: Path | None = None  # Root of the skill folder (for script resolution)
    scripts: dict[str, Path] = field(default_factory=dict)  # script_name -> absolute path

    def to_context_section(self) -> str:
        """Render skill as a section for injection into system prompt."""
        parts = [f"## Skill: {self.name}\n\n{self.content}"]
        if self.skill_dir is not None:
            parts.append(f"\n**Skill path**: {self.skill_dir}")
        if self.scripts:
            lines = []
            for name, path in sorted(self.scripts.items()):
                lines.append(f"- {name}: {path}")
            parts.append("\n**Available scripts**:\n" + "\n".join(lines))
        return "\n".join(parts)

    def get_script_path(self, script_name: str) -> Path | None:
        """Resolve script name to path. Returns None if script not found or invalid."""
        path = self.scripts.get(script_name)
        if path is None:
            return None
        try:
            resolved = path.resolve()
            return resolved if resolved.is_file() else None
        except Exception:
            return None


__all__ = ["Skill"]
