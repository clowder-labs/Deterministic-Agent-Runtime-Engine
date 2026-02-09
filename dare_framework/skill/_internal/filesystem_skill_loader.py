"""Filesystem-based skill loader (Agent Skills format)."""

from __future__ import annotations

from pathlib import Path

from dare_framework.skill import ISkillLoader
from dare_framework.skill.types import Skill
from dare_framework.skill._internal._skill_parser import parse_skill_md


class FileSystemSkillLoader(ISkillLoader):
    """Loads skills from directories containing SKILL.md files."""

    def __init__(self, *paths: str | Path) -> None:
        """Initialize with one or more root paths to scan for skill directories.

        Each path can be a directory containing skill subdirs, or a direct skill dir
        with SKILL.md.
        """
        self._paths = [Path(path) for path in paths]

    def load(self) -> list[Skill]:
        """Load and parse all skills from configured paths."""
        skills: list[Skill] = []
        seen_ids: set[str] = set()

        for root in self._paths:
            if not root.exists():
                continue
            for skill_dir in self._iter_skill_dirs(root):
                skill = self._load_skill(skill_dir)
                if skill and skill.id not in seen_ids:
                    skills.append(skill)
                    seen_ids.add(skill.id)

        return skills

    def _iter_skill_dirs(self, root: Path):
        """Yield directories that contain SKILL.md."""
        if not root.is_dir():
            return
        skill_md = root / "SKILL.md"
        if skill_md.exists():
            yield root
        for child in root.iterdir():
            if child.is_dir():
                if (child / "SKILL.md").exists():
                    yield child
                else:
                    yield from self._iter_skill_dirs(child)

    def _load_skill(self, skill_dir: Path) -> Skill | None:
        """Parse a single skill directory including scripts/."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            return None

        frontmatter, body = parse_skill_md(content)
        name = frontmatter.get("name", "").strip() or skill_dir.name
        description = frontmatter.get("description", "").strip()

        if not description and not body:
            return None

        skill_id = name.lower().replace(" ", "-").replace("_", "-")
        scripts = self._load_scripts(skill_dir)
        skill_dir_resolved = skill_dir.resolve()

        return Skill(
            id=skill_id,
            name=name,
            description=description,
            content=body,
            skill_dir=skill_dir_resolved,
            scripts=scripts,
        )

    def _load_scripts(self, skill_dir: Path) -> dict[str, Path]:
        """Load script paths from skill_dir/scripts/. Returns dict mapping name (stem) -> path."""
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.is_dir():
            return {}
        result: dict[str, Path] = {}
        for path in scripts_dir.iterdir():
            if path.is_file() and not path.name.startswith("."):
                stem = path.stem
                if stem:
                    result[stem] = path.resolve()
        return result


__all__ = ["FileSystemSkillLoader"]
