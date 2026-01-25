## Context
- The v3.4 config domain only exposes `ConfigSnapshot(values: dict)` without a typed model.
- v3.x config modules use dataclass-based config models with component-type routing.
- Runtime managers need a single, effective config snapshot derived from layered sources.

## Goals / Non-Goals
- Goals:
  - Provide a unified, typed runtime Config model for dare_framework3_4.
  - Support manager-driven component enablement and per-component configuration.
- Capture model adapter settings, MCP connection config, and proxy settings (http/https/no_proxy/use_system_proxy/disabled) in a single schema.
  - Ensure the effective Config snapshot is immutable at runtime.
- Non-Goals:
  - Implement config file loading or layer merging logic.
  - Introduce runtime budget management.
  - Change manager interfaces beyond config access expectations.

## Decisions
- Use frozen dataclasses for LLMConfig, ComponentConfig, Config, and ConfigSnapshot to keep runtime config immutable.
- Introduce ComponentType enum to centralize component type identifiers; new component types only require enum additions.
- Store component enablement and per-component config under `components.<type>` with a `disabled` list plus named entries.
- Add proxy configuration under `llm` (e.g., `llm.proxy.http` / `llm.proxy.https` / `llm.proxy.no_proxy` / `llm.proxy.use_system_proxy` / `llm.proxy.disabled`) for outbound model adapter requests.
- Keep optional fields with defaults to preserve backwards compatibility when partial config is provided.

## Risks / Trade-offs
- Schema expansion increases validation surface area; mitigate via optional fields and explicit defaults.
- Proxy field naming may vary across deployments; confirm expected structure before implementation.

## Migration Plan
- Introduce the config dataclasses and update ConfigSnapshot to carry the effective Config.
- Update any config-provider code to build a Config from layered dicts.
- Update managers to read component enablement and per-component settings from Config.

## Open Questions
- None.
