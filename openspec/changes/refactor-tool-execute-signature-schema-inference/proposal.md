# Change: Make tool execute signature the source of truth for schemas

## Why
Tool implementations currently duplicate parameter contracts in two places: `execute(input: dict, context)` and explicit `input_schema`/`output_schema` properties. This duplication allows drift and weakens readability for both humans and model-facing metadata.

## What Changes
- **BREAKING** Change `ITool.execute(...)` from dict payload style to keyword-parameter style with explicit `run_context`.
- Add automatic schema inference from `execute` type annotations:
  - input schema inferred from `execute` parameters (excluding `self` and `run_context`)
  - output schema inferred from `ToolResult[T]` return annotation
- Add docstring-based field description extraction so schema descriptions come from parameter comments, while type/required-ness come from signature.
- Update `ToolGateway` invocation to call tools via keyword args (`tool.execute(run_context=..., **params)`).
- Migrate built-in tools and core tests to the new execute contract.

## Impact
- Affected specs: `interface-layer`, `component-management`
- Affected code: `dare_framework/tool/kernel.py`, `dare_framework/tool/types.py`, `dare_framework/tool/tool_gateway.py`, built-in tool implementations, tool-related unit tests
