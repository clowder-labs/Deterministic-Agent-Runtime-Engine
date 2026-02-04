## Context
The current package layout places most interfaces and data models in single files and exposes many top-level modules that only re-export deeper symbols. This blurs the three-layer architecture described in `docs/design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md` and `docs/design/archive/Architecture_Final_Review_v1.3.md`, and makes it harder to locate core contracts during the ongoing interface/model design phase.

## Pythonic Organization References
To make the layout more idiomatic for Python contributors, the re-organization follows common library patterns (explicit subpackages by domain, minimal `__init__.py` files, and no re-export glue). This aligns with how mature Python libraries keep entry points obvious while preserving internal modularity, without relying on deep inheritance hierarchies or overly broad modules.

## Goals / Non-Goals
- Goals:
  - Make the three-layer model visible in the package layout.
  - Split core interfaces and models into domain-focused modules.
  - Remove unused pass-through re-export modules.
  - Add concise design-intent comments to interfaces and abstract methods, aligned with the design docs.
- Non-Goals:
  - Change runtime behavior or introduce new features.
  - Preserve legacy import compatibility (development-only codebase).
  - Re-implement components beyond structural moves and documentation updates.

## Decisions
- Use explicit layer namespaces:
  - Layer 1 (Core Infrastructure): `dare_framework/core/`
  - Layer 2 (Pluggable Components): `dare_framework/components/`
  - Layer 3 (Agent Composition): `dare_framework/composition/` (builder, component managers, wiring).
- Flatten core contracts into explicit modules under `dare_framework/core/`:
  - `dare_framework/core/` includes interface modules by domain (runtime, tooling, policy, planning, validation, trust boundary, context, MCP, config, registries, composition).
  - `dare_framework/core/models/` split by config, runtime, plan, tool, event, context, MCP, memory, and result types.
- Remove top-level re-export-only modules (e.g., `dare_framework/errors.py`, `dare_framework/models.py`, `dare_framework/interfaces.py`, `dare_framework/runtime.py`, `dare_framework/tool_runtime.py`). Import paths should use explicit module locations instead of package re-exports.
- Keep the module tree shallow (no more than two levels beneath each layer) to avoid over-segmentation.
- Add brief docstrings/comments on each interface and abstract method explaining intent, trust boundaries, and layer role, citing the design docs where relevant.
- Keep package `__init__.py` files minimal (docstring-only or module exposure) and avoid re-exporting implementation classes.
- Introduce `ITrustBoundary` in `dare_framework/core/trust_boundary.py` to model the design-doc trust boundary step (derive safety-critical fields from registries before policy checks).
- Introduce `IToolRegistry` in `dare_framework/core/registries.py` to express the trusted source for tool metadata required by TrustBoundary and PolicyEngine.
- Separate proposal-stage vs validated plan structures by removing the `PlanStep = ProposedStep` alias, keeping explicit `ProposedStep` and `ValidatedStep` models.
- Allow placeholder packages only when they include a clear module-level docstring describing intent and expected contents.
- Rename the runtime implementation module to `runtime_engine.py` so `core/runtime.py` can host the runtime interfaces without circular imports.
- Split plugin-loaded component types into subpackages (validators, memory, model_adapters, mcp_clients, hooks, config_providers, prompt_stores, tools, skills).

## Alternatives Considered
- Keep re-export modules for compatibility. Rejected because compatibility is not required and the re-exports obscure the new layered structure.
- Minimal refactor limited to comments. Rejected because file layout is the primary source of confusion.

## Risks / Trade-offs
- Import churn across examples/tests; mitigated by updating all internal references in the same change.
- Potential circular imports when splitting models; mitigated by grouping related models and using local imports where needed.
- Over-segmentation could reduce readability; mitigated by keeping domain modules cohesive and avoiding excessive nesting.

## Migration Plan
1. Define the target module tree and move interface/model definitions into domain-focused modules.
2. Update imports throughout the codebase to the new module paths.
3. Remove pass-through modules and keep package `__init__.py` files minimal.
4. Add design-intent comments to interfaces and abstract methods.
5. Run tests and fix any import or type issues.

## Interface Contract Sketches (for clarity)
These sketches are non-binding but define the intended shape of core contracts.

```
IToolRegistry:
  get_tool_definition(name: str) -> ToolDefinition | None
  list_tool_definitions() -> list[ToolDefinition]

ITrustBoundary:
  derive_step(proposed_step: ProposedStep, registry: IToolRegistry) -> ValidatedStep
  derive_plan(proposed_plan: ProposedPlan, registry: IToolRegistry) -> ValidatedPlan
  # failures reported via structured errors (exact mechanism in core errors)
```

## Target Module Map (Draft)
```
dare_framework/
  core/
    composition.py
    config.py
    context.py
    mcp.py
    planning.py
    policy.py
    registries.py
    runtime.py
    runtime_engine.py
    tooling.py
    trust_boundary.py
    validation.py
    models/
      config.py
      runtime.py
      plan.py
      tool.py
      event.py
      context.py
      mcp.py
      memory.py
      results.py
    errors.py
  components/
    validators/
    memory/
    model_adapters/
    tools/
    skills/
    mcp_clients/
    hooks/
    config_providers/
    prompt_stores/
    checkpoint.py
    context_assembler.py
    event_log.py
    mcp_toolkit.py
    plan_generator.py
    policy_engine.py
    registries.py
    remediator.py
    tool_runtime.py
  composition/
    builder.py
    component_manager.py
```

## Open Questions
- None.
