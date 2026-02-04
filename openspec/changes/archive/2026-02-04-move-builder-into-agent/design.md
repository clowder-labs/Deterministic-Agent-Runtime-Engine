## Context
The agent composition API is currently exposed through a standalone builder package. The desired developer experience is to treat agent composition as part of the agent domain, with `BaseAgent` serving as the primary entry point for selecting builder variants.

## Goals / Non-Goals
- Goals:
  - Preserve existing builder logic and resolution semantics.
  - Move builder API into the agent domain and remove the standalone builder package.
  - Expose builder factories on `BaseAgent` for simple discovery and usage.
  - Keep built-in agents inheriting from `BaseAgent`.
- Non-Goals:
  - Introducing new builder behavior or changing resolution rules.
  - Providing compatibility shims for the removed `dare_framework.builder` package.

## Decisions
- Decision: Move `BaseAgent` out of `_internal` into a public agent module (proposed filename: `base_agent.py`).
  - Rationale: `BaseAgent` is a public developer surface and should not be hidden under `_internal`.
- Decision: Relocate builder implementation into the agent domain (e.g., `dare_framework/agent/builder.py`) and remove the `dare_framework/builder` package.
  - Rationale: Composition is an agent-domain concern and should not be a separate top-level domain.
- Decision: Replace the `Builder` facade with `BaseAgent.simple_chat_agent_builder(...)` and `BaseAgent.five_layer_agent_builder(...)`.
  - Rationale: Provides a single, discoverable entry point on the primary agent base class.

## Alternatives considered
- Keep `Builder` as a deprecated compatibility wrapper.
  - Rejected: request explicitly removes the module, and compatibility shims extend the migration surface.
- Keep `BaseAgent` in `_internal` and re-export via `agent.__init__`.
  - Rejected: conflicts with the intent of `_internal` and obscures the public base class.

## Risks / Trade-offs
- Breaking change for downstream imports (`from dare_framework.builder import Builder`).
  - Mitigation: Update all in-repo examples/tests/docs and document migration steps in proposal.
- File naming ambiguity for the new `BaseAgent` module.
  - Mitigation: Use snake_case (`base_agent.py`) unless explicitly requested otherwise.

## Migration Plan
1. Move `BaseAgent` to a public agent module and update all imports.
2. Move builder implementation into the agent domain and remove `dare_framework/builder`.
3. Add builder factory methods on `BaseAgent`.
4. Update examples/tests/docs to import from `dare_framework.agent` and call `BaseAgent.*_agent_builder`.
5. Validate with unit tests and example runs where feasible.

## Open Questions
- Confirm final filename for the BaseAgent module (`base_agent.py` vs `baseAgent.py`).
