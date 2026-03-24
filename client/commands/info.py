"""Informational and utility command handlers."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from dare_framework.config import Config
from client.runtime.action_client import TransportActionClient
from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.interaction.resource_action import ResourceAction


async def list_tools(*, action_client: TransportActionClient) -> dict[str, Any]:
    return await action_client.invoke_action(ResourceAction.TOOLS_LIST)


async def list_skills(*, action_client: TransportActionClient) -> dict[str, Any]:
    return await action_client.invoke_action(ResourceAction.SKILLS_LIST)


async def show_config(*, action_client: TransportActionClient) -> dict[str, Any]:
    return await action_client.invoke_action(ResourceAction.CONFIG_GET)


async def show_model(*, action_client: TransportActionClient) -> dict[str, Any]:
    return await action_client.invoke_action(ResourceAction.MODEL_GET)


async def send_control(
    control: str,
    *,
    action_client: TransportActionClient,
) -> dict[str, Any]:
    normalized = control.strip().lower()
    resolved = AgentControl.value_of(normalized)
    if resolved is None:
        raise ValueError(f"unsupported control: {control}")
    result = await action_client.invoke_control(resolved)
    return {"control": resolved.value, "result": result}


def build_doctor_report(
    *,
    config: Config,
    model_probe_error: str | None = None,
) -> dict[str, Any]:
    """Return deterministic environment diagnostics from effective config."""
    adapter = (config.llm.adapter or "openai").lower()
    api_key_sources = {
        "openrouter": bool(config.llm.api_key or os.getenv("OPENROUTER_API_KEY")),
        "openai": bool(config.llm.api_key or os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(config.llm.api_key or os.getenv("ANTHROPIC_API_KEY")),
        "huawei-modelarts": bool(
            config.llm.api_key or os.getenv("HUAWEI_MODELARTS_API_KEY")
        ),
    }
    workspace = Path(config.workspace_dir).expanduser().resolve()
    user_dir = Path(config.user_dir).expanduser().resolve()
    workspace_config = workspace / ".dare" / "config.json"
    user_config = user_dir / ".dare" / "config.json"
    mcp_path_states = []
    for raw in config.mcp_paths:
        path = Path(raw).expanduser().resolve()
        mcp_path_states.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "is_dir": path.is_dir(),
            }
        )

    deps = {
        "httpx_installed": importlib.util.find_spec("httpx") is not None,
        "openai_sdk_installed": importlib.util.find_spec("openai") is not None,
        "langchain_openai_installed": importlib.util.find_spec("langchain_openai") is not None,
        "anthropic_sdk_installed": importlib.util.find_spec("anthropic") is not None,
    }

    diagnostics: dict[str, Any] = {
        "workspace_dir": str(workspace),
        "workspace_exists": workspace.exists(),
        "user_dir": str(user_dir),
        "user_exists": user_dir.exists(),
        "config_files": {
            "workspace": {"path": str(workspace_config), "exists": workspace_config.exists()},
            "user": {"path": str(user_config), "exists": user_config.exists()},
        },
        "llm": {
            "adapter": adapter,
            "model": config.llm.model,
            "endpoint": config.llm.endpoint,
            "api_key_present": api_key_sources.get(adapter, False),
        },
        "mcp_paths": mcp_path_states,
        "dependencies": deps,
    }
    warnings: list[str] = []
    if not diagnostics["workspace_exists"]:
        warnings.append("workspace_dir does not exist")
    if adapter not in {"openai", "openrouter", "anthropic", "huawei-modelarts"}:
        warnings.append(f"unsupported adapter configured: {adapter}")
    if not diagnostics["llm"]["api_key_present"]:
        warnings.append(f"missing API key for adapter={adapter}")
    if model_probe_error is not None:
        warnings.append(f"model adapter probe failed: {model_probe_error}")
    for mcp_state in mcp_path_states:
        if not mcp_state["exists"]:
            warnings.append(f"mcp_path does not exist: {mcp_state['path']}")
            continue
        if not mcp_state["is_dir"]:
            warnings.append(f"mcp_path is not a directory: {mcp_state['path']}")
    if adapter == "openrouter" and not deps["openai_sdk_installed"]:
        warnings.append("openai SDK is required for openrouter adapter")
    if adapter == "openai" and not deps["langchain_openai_installed"]:
        warnings.append("langchain-openai is required for openai adapter")
    if adapter == "anthropic" and not deps["anthropic_sdk_installed"]:
        warnings.append("anthropic SDK is required for anthropic adapter")
    if adapter == "huawei-modelarts" and not deps["openai_sdk_installed"]:
        warnings.append("openai SDK is required for huawei-modelarts adapter")
    diagnostics["warnings"] = warnings
    diagnostics["ok"] = len(warnings) == 0
    return diagnostics
