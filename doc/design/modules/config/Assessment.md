# Config Domain Assessment

> Status: draft (2026-02-03). Scope: `dare_framework/config` only.

## 1. Scope & Responsibilities

- Define the effective configuration model (`Config`).
- Provide a provider interface to load/refresh config snapshots.
- Support component enable/disable and per‑component settings.

## 2. Current Public Surface (Facade)

`dare_framework.config` exports:
- Types: `Config`, `LLMConfig`, `ProxyConfig`, `ComponentConfig`,
  `ObservabilityConfig`, `RedactionConfig`
- Interface: `IConfigProvider`
- Factory: `build_config_provider`
- Default implementation: `FileConfigProvider`

## 3. Actual Dependencies

- **Agent/Builder**: `Config` drives model/tool/hook/planner selection and prompt/skill defaults.
- **Infra**: `ComponentType` + `IComponent` are used for enable/disable checks.
- **MCP/Skill**: config fields such as `mcp_paths`, `allowmcps`, `skill_mode`, `skill_paths`.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Default provider exposure**
   - `FileConfigProvider` is exposed as the default implementation.
   - This keeps ergonomics but expands the public surface.

2. **Component config typing is loose**
   - `component_config()` returns `Any`, leaving schema undefined.
   - Doc gap remains until component schemas are formalized.

3. **Layered config scope is minimal**
   - Current provider merges only user + workspace JSON layers.
   - Spec mentions system/project/user/session layering; still a future gap.

## 5. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.config`**:
  - `IConfigProvider`
  - `Config` and config dataclasses
  - `build_config_provider`

## 5.1 Default Implementation

- `FileConfigProvider` lives in `dare_framework/config/file_config_provider.py`.

## 6. Doc Updates Needed

- `doc/design/modules/config/README.md`: clarify default provider location.
- `doc/design/Framework_MinSurface_Review.md`: reflect facade reduction.

## 7. Proposed Implementation Plan (Config Domain)

1. Keep `FileConfigProvider` in the config facade for convenience.
2. Keep `build_config_provider` as the supported factory entry.
3. Ensure docs/tests point to the top-level module.

## 8. Open Questions

- Should layered config expand to system/project/user/session to match spec?
- Should component configs be typed per component type?
