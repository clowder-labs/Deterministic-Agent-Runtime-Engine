from __future__ import annotations

from pathlib import Path

from dare_framework.config.types import Config
from dare_framework.skill import ISkillLoader, Skill, SkillStoreBuilder


class StaticSkillLoader(ISkillLoader):
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = list(skills)

    def load(self) -> list[Skill]:
        return list(self._skills)


def _write_skill(root: Path, skill_id: str, body: str) -> None:
    skill_dir = root / ".dare" / "skills" / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_skill_store_builder_composes_config_and_external_loaders(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    user_root = tmp_path / "user"
    _write_skill(workspace_root, "workspace-skill", "workspace skill body")
    _write_skill(user_root, "user-skill", "user skill body")

    external_skill = Skill(
        id="external-skill",
        name="external-skill",
        description="external",
        content="external body",
    )
    store = (
        SkillStoreBuilder.config(
            Config(workspace_dir=str(workspace_root), user_dir=str(user_root))
        )
        .with_skill_provider(StaticSkillLoader([external_skill]))
        .build()
    )

    ids = {skill.id for skill in store.list_skills()}
    assert "workspace-skill" in ids
    assert "user-skill" in ids
    assert "external-skill" in ids


def test_skill_store_builder_disable_skill_filters_final_store(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    user_root = tmp_path / "user"
    _write_skill(workspace_root, "workspace-skill", "workspace skill body")

    store = (
        SkillStoreBuilder.config(
            Config(workspace_dir=str(workspace_root), user_dir=str(user_root))
        )
        .disable_skill("workspace-skill")
        .build()
    )

    assert store.get_skill("workspace-skill") is None
    assert "workspace-skill" not in {skill.id for skill in store.list_skills()}
