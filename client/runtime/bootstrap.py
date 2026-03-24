"""Runtime bootstrap for the client CLI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from dare_framework.agent import DareAgentBuilder
from dare_framework.config import Config, FileConfigProvider
from dare_framework.model.default_model_adapter_manager import DefaultModelAdapterManager
from dare_framework.model.factories import create_default_prompt_store
from dare_framework.model.interfaces import IPromptStore
from dare_framework.model.types import Prompt
from dare_framework.plan import DefaultPlanner, DefaultRemediator
from dare_framework.tool._internal.tools import ReadFileTool, RunCommandTool, SearchCodeTool, WriteFileTool
from dare_framework.tool._internal.tools.ask_user import IUserInputHandler
from dare_framework.transport import AgentChannel, DirectClientChannel


@dataclass(frozen=True)
class RuntimeOptions:
    """CLI-provided runtime overrides."""

    workspace_dir: Path
    user_dir: Path
    model: str | None = None
    adapter: str | None = None
    api_key: str | None = None
    endpoint: str | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    mcp_paths: list[str] | None = None
    system_prompt_mode: str | None = None
    system_prompt_text: str | None = None
    system_prompt_file: str | None = None
    user_input_handler: IUserInputHandler | None = None


@dataclass
class ClientRuntime:
    """Initialized runtime object shared by command handlers."""

    agent: Any
    channel: AgentChannel
    client_channel: DirectClientChannel
    config_provider: FileConfigProvider
    config: Config
    model: Any
    options: RuntimeOptions

    async def close(self) -> None:
        """Gracefully stop agent/channel lifecycle."""
        await self.agent.stop()

    async def reload_config(self) -> Config:
        """Reload file-backed config and re-apply CLI overrides."""
        self.config = apply_runtime_overrides(self.config_provider.reload(), self.options)
        return self.config


def load_effective_config(options: RuntimeOptions) -> tuple[FileConfigProvider, Config]:
    """Load file-backed config and apply CLI overrides without building runtime."""
    provider = FileConfigProvider(
        workspace_dir=options.workspace_dir,
        user_dir=options.user_dir,
    )
    config = apply_runtime_overrides(provider.current(), options)
    return provider, config


def _normalize_mcp_paths(paths: list[str], base_dir: Path) -> list[str]:
    normalized: list[str] = []
    for raw in paths:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            # Keep config authoring friendly while runtime loading stays deterministic.
            p = (base_dir / p).resolve()
        normalized.append(str(p))
    return normalized


def _resolve_config_paths(config: Config, workspace_dir: Path) -> Config:
    if not config.mcp_paths:
        return config
    normalized = _normalize_mcp_paths(list(config.mcp_paths), workspace_dir)
    if normalized == list(config.mcp_paths):
        return config
    return replace(config, mcp_paths=normalized)


def apply_runtime_overrides(config: Config, options: RuntimeOptions) -> Config:
    """Apply CLI flags on top of file-backed Config."""
    effective = config
    effective = replace(
        effective,
        workspace_dir=str(options.workspace_dir),
        user_dir=str(options.user_dir),
    )
    effective = _resolve_config_paths(effective, options.workspace_dir)

    llm = effective.llm
    if options.model is not None:
        llm = replace(llm, model=options.model)
    if options.adapter is not None:
        llm = replace(llm, adapter=options.adapter)
    if options.api_key is not None:
        llm = replace(llm, api_key=options.api_key)
    if options.endpoint is not None:
        llm = replace(llm, endpoint=options.endpoint)
    if options.max_tokens is not None:
        llm = replace(llm, extra={**dict(llm.extra), "max_tokens": int(options.max_tokens)})
    effective = replace(effective, llm=llm)

    if options.mcp_paths:
        effective = replace(
            effective,
            mcp_paths=_normalize_mcp_paths(list(options.mcp_paths), options.workspace_dir),
        )
    system_prompt = effective.system_prompt
    cli_mode: str | None = None
    if options.system_prompt_mode is not None:
        normalized_mode = options.system_prompt_mode.strip().lower()
        if normalized_mode not in {"replace", "append"}:
            raise ValueError(f"invalid system prompt mode: {options.system_prompt_mode}")
        cli_mode = normalized_mode
        system_prompt = replace(
            system_prompt,
            mode="replace" if normalized_mode == "replace" else "append",
        )
    if options.system_prompt_text is not None:
        # CLI text override is authoritative and clears file-based source.
        system_prompt = replace(system_prompt, content=options.system_prompt_text, path=None)
        if cli_mode is None:
            # Per CLI contract, text override without explicit mode defaults to replace.
            system_prompt = replace(system_prompt, mode="replace")
    if options.system_prompt_file is not None:
        # CLI file override is authoritative and clears inline source.
        system_prompt = replace(system_prompt, path=options.system_prompt_file, content=None)
        if cli_mode is None:
            # Per CLI contract, file override without explicit mode defaults to replace.
            system_prompt = replace(system_prompt, mode="replace")
    effective = replace(effective, system_prompt=system_prompt)
    return effective


def _resolve_system_prompt_content(config: Config) -> tuple[str, str] | None:
    """Resolve runtime system-prompt mode/content from effective config."""
    prompt_cfg = config.system_prompt
    if prompt_cfg.content is not None and prompt_cfg.path is not None:
        raise ValueError("system_prompt.content and system_prompt.path are mutually exclusive")

    content = prompt_cfg.content
    if prompt_cfg.path is not None:
        prompt_path = Path(prompt_cfg.path).expanduser()
        if not prompt_path.is_absolute():
            prompt_path = (Path(config.workspace_dir) / prompt_path).resolve()
        try:
            content = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"failed to read system_prompt.path: {prompt_path}: {exc}") from exc

    if content is None:
        return None

    mode = prompt_cfg.mode or "replace"
    if mode not in {"replace", "append"}:
        raise ValueError(f"invalid system_prompt.mode: {mode}")
    return mode, content


def _resolve_base_system_prompt(
    *,
    config: Config,
    model: Any,
    prompt_store: IPromptStore | None = None,
) -> Prompt:
    prompt_id = config.default_prompt_id or "base.system"
    model_name = getattr(model, "model", None) or getattr(model, "name", None)
    if not model_name:
        raise ValueError("model adapter must expose model/name for prompt resolution")
    store = prompt_store or create_default_prompt_store(config)
    try:
        return store.get(prompt_id, model=model_name)
    except KeyError as exc:
        raise ValueError(f"Prompt not found: {prompt_id}") from exc


def _resolve_system_prompt_override(
    *,
    config: Config,
    model: Any,
    prompt_store: IPromptStore | None = None,
) -> Prompt | None:
    """Build a runtime Prompt override from config system_prompt policy."""
    resolved = _resolve_system_prompt_content(config)
    if resolved is None:
        return None
    mode, user_content = resolved
    if mode == "replace":
        # Full replace mode should not depend on prompt-store availability.
        prompt_id = config.default_prompt_id or "base.system"
        return Prompt(
            prompt_id=prompt_id,
            role="system",
            content=user_content,
            supported_models=["*"],
            order=0,
        )

    base_prompt = _resolve_base_system_prompt(config=config, model=model, prompt_store=prompt_store)
    merged_content = base_prompt.content + "\n\n---\n\n" + user_content
    return Prompt(
        prompt_id=base_prompt.prompt_id,
        role=base_prompt.role,
        content=merged_content,
        supported_models=list(base_prompt.supported_models),
        order=base_prompt.order,
        version=base_prompt.version,
        name=base_prompt.name,
        metadata=dict(base_prompt.metadata),
    )


async def bootstrap_runtime(options: RuntimeOptions) -> ClientRuntime:
    """Build and start the agent runtime for CLI usage."""
    provider, config = load_effective_config(options)
    model_manager = DefaultModelAdapterManager(config=config)
    model = model_manager.load_model_adapter(config=config)
    if model is None:
        raise RuntimeError("model adapter manager returned no model adapter")

    client_channel = DirectClientChannel()
    channel = AgentChannel.build(client_channel)
    builder = (
        DareAgentBuilder("dare-client-cli")
        .with_config(config)
        .with_config_provider(provider)
        .with_model(model)
        .with_agent_channel(channel)
        .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool())
        .with_planner(DefaultPlanner(model, verbose=False))
        .with_remediator(DefaultRemediator(model, verbose=False))
    )
    if options.user_input_handler is not None:
        builder = builder.with_user_input_handler(options.user_input_handler)
    prompt_override = _resolve_system_prompt_override(config=config, model=model)
    if prompt_override is not None:
        builder = builder.with_prompt(prompt_override)
    agent = await builder.build()
    await agent.start()
    return ClientRuntime(
        agent=agent,
        channel=channel,
        client_channel=client_channel,
        config_provider=provider,
        config=config,
        model=model,
        options=options,
    )
