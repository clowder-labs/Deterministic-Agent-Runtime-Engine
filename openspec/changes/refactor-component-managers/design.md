## Context
DARE Framework uses IComponent-based pluggables and entry points for discovery. The current implementation uses a single ComponentManager with hardcoded type routing. The target design is per-interface managers that share common discovery and lifecycle logic via a base class, aligned with the three-layer architecture.

## Goals / Non-Goals
- Goals:
  - Split component management into per-interface managers.
  - Provide a BaseComponentManager with common load/init/register logic.
  - Always use entry points for discovery (no enable/disable config).
  - Each manager returns an ordered list of its managed components given an IConfigProvider.
- Non-Goals:
  - Compatibility layer for the old ComponentManager.
  - Hot-reload support in this iteration.

## Decisions
- Decision: Introduce BaseComponentManager to encapsulate entry point discovery, ordering, initialization, and registration.
  - Rationale: Remove duplicated loader logic and avoid hardcoded branching.
- Decision: Create one manager per IComponent type (validators, memory, model adapters, tools, skills, MCP clients, hooks, config providers, prompt stores).
  - Rationale: Clear responsibility boundaries and extensibility without a central switch.
- Decision: Managers are always discovery-enabled and accept IConfigProvider input.
  - Rationale: Align with plug-in design and centralized configuration.
- Decision: Remove ComponentManager and ComponentDiscoveryConfig without compatibility.
  - Rationale: Early-stage refactor with no backward-compat requirements.

## Manager Interface Sketch
- BaseComponentManager:
  - load(config_provider) -> list[IComponent]
  - init/register ordering by ascending IComponent.order
  - entry point group is defined by the subclass

- XxxComponentManager (Validator/Memory/ModelAdapter/etc.):
  - inherits BaseComponentManager
  - returns typed list (e.g., list[IValidator])

## Risks / Trade-offs
- Risk: Always-on discovery may load unintended plugins. Mitigation: document entry point namespaces and default packaging expectations.

## Migration Plan
1. Implement BaseComponentManager and per-type managers.
2. Update builder wiring to use specific managers.
3. Remove old ComponentManager/ComponentDiscoveryConfig.
4. Update docs and tests.
