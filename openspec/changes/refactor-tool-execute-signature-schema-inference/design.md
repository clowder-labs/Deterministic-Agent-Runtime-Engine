## Context
Tool contracts currently require manual schema declarations plus dict-based execute payloads. This duplicates intent and introduces mismatch risk.

## Goals / Non-Goals
- Goals:
  - Make `execute` signature and annotations authoritative for tool parameter contracts.
  - Keep doc comments as descriptive metadata, not type authority.
  - Ensure model-facing schemas stay aligned with execution behavior.
- Non-Goals:
  - Introduce a new schema DSL.
  - Add legacy compatibility shims for old execute signatures.

## Decisions
- Decision: `ITool.execute` uses keyword arguments with a required `run_context` keyword-only parameter.
- Decision: `ITool.input_schema` and `ITool.output_schema` default to inferred values from `execute`.
- Decision: `ToolResult` becomes generic (`ToolResult[TOutput]`) to support output-schema inference from return type annotations.
- Decision: schema inference supports core typing forms (`str/int/float/bool`, `Optional`, `Literal`, `list`, `dict`, `TypedDict`, and unions).

## Risks / Trade-offs
- **Breaking API**: all tool implementations and test doubles must migrate signature style.
- **Inference edge cases**: very complex annotations may degrade to permissive object schemas.

## Migration Plan
1. Add schema inference utilities and generic `ToolResult` typing.
2. Update `ITool` contract and `ToolGateway` invocation path.
3. Migrate built-in tools to explicit execute kwargs and return typing.
4. Update tests/dummies and validate targeted suites.

## Open Questions
- Should schema inference eventually support richer metadata providers (e.g., Annotated constraints) in a follow-up?
