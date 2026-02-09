"""Build A2A AgentCard from DARE config and skills (a2acn.com/docs/concepts/agentcard)."""

from __future__ import annotations

from typing import Any

from dare_framework.a2a.types import AgentCardDict, AgentSkillDict
from dare_framework.config.types import Config
from dare_framework.skill import SkillStoreBuilder
from dare_framework.skill.types import Skill


def _skill_to_agent_skill(skill: Skill) -> AgentSkillDict:
    """Map DARE Skill to A2A AgentSkill."""
    return AgentSkillDict(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        inputModes=["text/plain"],
        outputModes=["text/plain"],
        examples=[],
    )


def _load_skills_from_config(config: Config) -> list[Skill]:
    """Load skills from default config-derived workspace/user skill roots."""
    store = SkillStoreBuilder.config(config).build()
    return store.list_skills()


def build_agent_card(
    config: Config,
    base_url: str,
    *,
    name: str | None = None,
    description: str | None = None,
    provider: str | None = None,
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Build A2A AgentCard JSON from DARE config and loaded skills.

    Args:
        config: DARE resolved config (workspace_dir, user_dir).
        base_url: Public base URL for this A2A server (e.g. https://host:port).
        name: Agent display name; default "DARE Agent".
        description: Agent description; default from workspace or generic.
        provider: Optional provider string.
        capabilities: Optional list e.g. ["streaming"]; default ["streaming"].

    Returns:
        AgentCard as a JSON-serializable dict for /.well-known/agent.json.
    """
    skills = _load_skills_from_config(config)
    agent_skills = [_skill_to_agent_skill(s) for s in skills]

    # Ensure base_url has no trailing slash for well-known path
    url = base_url.rstrip("/")

    # Override from config.a2a when not passed explicitly
    a2a = getattr(config, "a2a", None) or {}
    card_name = name if name is not None else a2a.get("name") or "DARE Agent"
    card_description = description if description is not None else a2a.get("description") or f"DARE agent at {url}"
    card_provider = provider if provider is not None else a2a.get("provider")
    card_capabilities = capabilities if capabilities is not None else a2a.get("capabilities") or ["streaming"]

    card: AgentCardDict = {
        "name": card_name,
        "description": card_description,
        "url": url,
        "version": "0.1.0",
        "capabilities": card_capabilities if isinstance(card_capabilities, list) else ["streaming"],
        "skills": agent_skills,
    }
    if card_provider:
        card["provider"] = card_provider
    auth = a2a.get("auth")
    if isinstance(auth, dict):
        card["auth"] = auth
    return dict(card)
