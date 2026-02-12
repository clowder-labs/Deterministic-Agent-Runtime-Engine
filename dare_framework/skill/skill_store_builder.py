"""Builder for constructing a SkillStore from config and custom loaders."""

from __future__ import annotations

from pathlib import Path

from dare_framework.config.types import Config
from dare_framework.skill.interfaces import ISkillLoader, ISkillStore
from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader
from dare_framework.skill._internal.skill_store import SkillStore

DEFAULT_WORKSPACE_SKILL_DIR = ".dare/skills"
DEFAULT_USER_SKILL_DIR = ".dare/skills"


class SkillStoreBuilder:
    """Compose loaders and filtering rules, then build an ISkillStore."""

    def __init__(self) -> None:
        self._config: Config | None = None
        self._skill_loaders: list[ISkillLoader] = []
        self._disabled_skill_ids: set[str] = set()

    @classmethod
    def config(cls, config: Config) -> SkillStoreBuilder:
        """Construct a builder with a runtime config for default filesystem loading."""
        return cls().with_config(config)

    def with_config(self, config: Config) -> SkillStoreBuilder:
        """Attach config for default filesystem-based skill loading."""
        self._config = config
        return self

    def with_skill_provider(self, skill_loader: ISkillLoader) -> SkillStoreBuilder:
        """Append an external skill loader."""
        self._skill_loaders.append(skill_loader)
        return self

    def with_skill_loader(self, skill_loader: ISkillLoader) -> SkillStoreBuilder:
        """Alias of with_skill_provider for clearer naming."""
        return self.with_skill_provider(skill_loader)

    def disable_skill(self, *skill_ids: str) -> SkillStoreBuilder:
        """Disable one or more skill ids from the final store."""
        for skill_id in skill_ids:
            normalized = skill_id.strip()
            if normalized:
                self._disabled_skill_ids.add(normalized)
        return self

    def build(self) -> ISkillStore:
        """Build and return the composed skill store."""
        loaders: list[ISkillLoader] = []
        if self._config is not None:
            workspace_root = Path(self._config.workspace_dir).resolve()
            user_root = Path(self._config.user_dir).resolve()
            if getattr(self._config, "skill_paths", None):
                resolved = []
                for p in self._config.skill_paths:
                    path = Path(p).expanduser()
                    if not path.is_absolute():
                        path = (workspace_root / path).resolve()
                    resolved.append(path)
                loaders.append(FileSystemSkillLoader(*resolved))
            else:
                loaders.append(
                    FileSystemSkillLoader(
                        workspace_root / DEFAULT_WORKSPACE_SKILL_DIR,
                        user_root / DEFAULT_USER_SKILL_DIR,
                    )
                )
        loaders.extend(self._skill_loaders)
        return SkillStore(
            skill_loaders=loaders,
            disabled_skill_ids=self._disabled_skill_ids,
        )


__all__ = ["SkillStoreBuilder"]
