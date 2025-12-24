## Context
DARE Framework follows a three-layer architecture. Core Infrastructure (Layer 1) should only define interfaces and runtime orchestration without plugin discovery. Pluggable Components (Layer 2) contain concrete implementations, and Agent Composition (Layer 3) wires implementations together. Today, the layering is clear but there is no unified lifecycle/registration protocol for pluggable components, and discovery is manual.

## Goals / Non-Goals
- Goals:
  - Define a unified component lifecycle contract for pluggable components.
  - Add a Layer 3 ComponentManager that performs discovery, ordering, initialization, and registration.
  - Support entry point-based discovery across pluggable interfaces (Python-native plugin mechanism).
  - Introduce composite validation with ordered chaining and aggregated errors.
  - Define configuration and prompt management interfaces for consistency.
- Non-Goals:
  - Implement hot reload in the first iteration.
  - Change the runtime execution semantics.
  - Require core to import or scan plugin implementations.

## Decisions
- Decision: Add `IComponent` as a base interface with `order` (ascending priority), `init`, and `register`, and have Layer 2 pluggables implement it.
  - Rationale: Provides consistent lifecycle/registration hooks across Layer 2 components (IModelAdapter, IMemory, IValidator, ITool, ISkill, IMCPClient, IHook, IConfigProvider, IPromptStore) without changing core runtime semantics.
- Decision: Component discovery uses entry points, but remains in Layer 3.
  - Rationale: Preserves Core purity, aligns with Python community patterns, allows third-party extensions.
- Decision: ComponentManager owns lifecycle only for instances it creates.
  - Rationale: Avoids double-close; aligns with “caller owns injected instances”.
- Decision: CompositeValidator is the default validator implementation in Layer 2.
  - Rationale: Encourages extensibility (custom validators chained with built-ins).
- Decision: Add `IConfigProvider` and `IPromptStore` interfaces.
  - Rationale: Centralize configuration/prompt management to avoid ad hoc adapters.

## Component Discovery (Entry Points)
ComponentManager discovers implementations via entry points grouped by interface type (e.g., `dare_framework.validators`, `dare_framework.memory`, `dare_framework.model_adapters`, `dare_framework.tools`, `dare_framework.skills`, `dare_framework.mcp_clients`, `dare_framework.hooks`, `dare_framework.config_providers`, `dare_framework.prompt_stores`). All discovered implementations are expected to implement `IComponent`.

Ordering: lower `order` executes first. ComponentManager sorts discovered components ascending by `order` before initialization and registration.

## Lifecycle Boundaries
- Instances created by ComponentManager: manager calls `init()` (async) before `register()` and calls `close()` (async) on shutdown.
- Instances injected explicitly by the caller: ComponentManager will register but will not assume ownership or call `close()`.

## Risks / Trade-offs
- Risk: Entry point discovery can introduce implicit dependencies. Mitigation: explicit configuration allowing discovery to be disabled or filtered.
- Risk: CompositeValidator ordering ambiguity. Mitigation: document order semantics and expose configuration for validator ordering.

## Migration Plan
1. Add `IComponent`, `IConfigProvider`, `IPromptStore` interfaces.
2. Add ComponentManager in Layer 3, wire into AgentBuilder.
3. Introduce CompositeValidator and update tests.
4. Update docs to reflect entry point discovery and component lifecycle.

## Open Questions
- Should entry point discovery be on by default or opt-in via config?
- Do we want a shared ComponentRegistry abstraction or keep per-registry registration?
