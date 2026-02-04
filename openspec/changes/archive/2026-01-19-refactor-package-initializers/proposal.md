# Change: Refactor package initializers

## Why
The current codebase mixes three different responsibilities into package initializers:
1) defining contracts (enums/dataclasses/`Protocol` interfaces) directly in `__init__.py`,
2) using `__init__.py` as a re-export surface (import glue + `__all__`), and
3) maintaining pass-through “re-export modules” whose only job is forwarding symbols.

Concrete findings from the current tree (post `c4b18582`):
- There are 29 `__init__.py` files under `dare_framework/`.
- 8 of them contain top-level `class` definitions (all under `dare_framework/core/*/__init__.py`), which makes
  “package initializer” double as “module of definition”.
- Several `components/*/__init__.py` files re-export implementation classes (e.g., `NoOp*`), which blurs what
  is an interface vs. an implementation and hides the module-of-definition.
- `components/memory/protocols.py` and `components/mcp_clients/protocols.py` are pass-through re-exports of
  contracts, which adds indirection without adding semantics.

This makes the project harder to navigate and undermines the “clean files / clear ownership” goal in
`docs/design/archive/Architecture_Final_Review_v2.1.md` and prior OpenSpec deltas (e.g., “Minimal Package Initializers”
and “No Pass-through Modules”).

## What Changes
- Remove compatibility constraints: update all internal imports to module-of-definition paths.
- Make every package initializer under `dare_framework/**/__init__.py` metadata-focused, allowing only
  metadata constants and no imports or re-exports.
- For Kernel domains that currently define contracts in `__init__.py`, move contracts into dedicated modules:
  - `models.py` (enums/dataclasses/value objects)
  - `protocols.py` (contract `Protocol` interfaces)
  - `errors.py` (domain exceptions, where applicable)
- Remove pass-through re-export modules (e.g., component `protocols.py` that only re-export contracts) and
  import from canonical contract modules directly.

## Impact
- Affected code: broad import-path churn across `dare_framework/`, `examples/`, and `tests/`.
- Affected specs: introduces/updates the `package-initializers` delta spec for initializer hygiene and
  module-of-definition imports.
- Primary risks:
  - Import cycles from refactors; mitigated by keeping `models.py` dependency-light and using forward
    references where needed.
  - Temporary developer friction from longer import paths; mitigated by consistent module naming.
