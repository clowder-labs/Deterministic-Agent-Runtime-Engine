# Change: Update runtime config model for dare_framework3_4

## Why
- dare_framework3_4 currently exposes only a dictionary-based ConfigSnapshot, which is insufficient for unified runtime configuration.
- Managers need a consistent, typed config to control component enablement (validators/hooks/skills) and to load model adapters and MCP connections.
- Aligns the runtime config model with v4.0 interface guidance and existing v3.x config patterns.

## What Changes
- Define typed config models in `dare_framework3_4/config/types.py` (LLMConfig, ComponentConfig, Config, ComponentType, plus proxy support) with `from_dict`/`to_dict` helpers.
- Update ConfigSnapshot to wrap the effective, immutable Config built from merged layers.
- Expand the config schema to cover runtime settings: llm (adapter/endpoint/api_key/model/proxy incl. no_proxy/use_system_proxy/disabled), mcp, tools, allow_tools, allow_mcps, components (type-scoped enable/disable + per-component config), workspace_dir, and user_dir.
- Managers consume components.<type>.disabled and per-component config to determine load behavior.

## Impact
- Affected specs: configuration-management
- Affected code: `dare_framework3_4/config/types.py`, `dare_framework3_4/config/__init__.py`, manager config lookups
