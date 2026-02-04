## Context
The v2 Kernel architecture organizes contracts and default implementations by functional domain under
`dare_framework/core/` (see `docs/design/archive/Architecture_Final_Review_v2.1.md`).

In `c4b18582`, several Kernel domains consolidated their contract type definitions (enums/dataclasses and
`Protocol` interfaces) directly into package `__init__.py` files:
- `dare_framework/core/budget/__init__.py`
- `dare_framework/core/context/__init__.py`
- `dare_framework/core/event/__init__.py`
- `dare_framework/core/execution_control/__init__.py`
- `dare_framework/core/hook/__init__.py`
- `dare_framework/core/orchestrator/__init__.py`
- `dare_framework/core/run_loop/__init__.py`
- `dare_framework/core/security/__init__.py`

This makes initializers “heavy” and inconsistent with other Kernel domains that already separate concerns
into dedicated modules (e.g., `core/plan/*`, `core/tool/*`).

Separately, several Layer 2 component packages use `__init__.py` as a re-export surface (imports + `__all__`)
for both contracts and concrete implementations (e.g., `NoOp*`), and a few files are pure pass-through
re-export modules (e.g., `components/memory/protocols.py` re-exporting the shared contract). This creates
multiple “public import surfaces” for the same symbol without clarifying ownership.

## Goals / Non-Goals
### Goals
- Make package initialization “boring”: no definitions; allow only metadata constants in `__init__.py`.
- Move Kernel contract definitions into dedicated modules with clear responsibility.
- Establish a consistent contract module pattern across Kernel domains (`models.py`, `protocols.py`, optional
  `errors.py`).
- Remove pass-through re-export modules and import from module-of-definition paths.
- Avoid behavioral changes and keep type checking/tests passing.

### Non-Goals
- Changing runtime behavior, loop semantics, or security policy logic.
- Renaming public contracts unless required for consistency.
- Reworking Layer 2 component packages beyond import adjustments needed for the refactor.

## Current State Findings (analysis)
This section captures the concrete issues observed in the current tree.

### 1) `__init__.py` used as a module-of-definition (Kernel)
There are 8 Kernel package initializers that contain contract definitions (top-level `class` statements),
instead of only providing a package boundary:
- `dare_framework/core/budget/__init__.py`
- `dare_framework/core/context/__init__.py`
- `dare_framework/core/event/__init__.py`
- `dare_framework/core/execution_control/__init__.py`
- `dare_framework/core/hook/__init__.py`
- `dare_framework/core/orchestrator/__init__.py`
- `dare_framework/core/run_loop/__init__.py`
- `dare_framework/core/security/__init__.py`

Consequence:
- A reader opening `__init__.py` (expecting package documentation) must instead read a full contract file.
- Tooling/search/navigation becomes less predictable: “go to definition” lands in initializers.

### 2) `__init__.py` used as a re-export surface (Layer 2 + some Kernel domains)
Several packages import-and-export symbols via `__init__.py` (imports + `__all__`), including concrete
implementations (e.g., `NoOp*` components) and aggregated type exports (e.g., `core/plan`).

Consequence:
- It becomes unclear which module owns a contract vs. an implementation.
- Imports become “magical” and harder to refactor safely because the module-of-definition is hidden.
- Import-time work grows (even when only the package is imported).

### 3) Pass-through re-export modules
Examples:
- `dare_framework/components/memory/protocols.py` re-exports `IMemory` from `dare_framework/contracts/memory.py`.
- `dare_framework/components/mcp_clients/protocols.py` re-exports `IMCPClient` from `dare_framework/contracts/mcp.py`.

Consequence:
- Adds indirection and extra import paths without adding semantics or ownership clarity.

## Proposed Decisions
### 1) `__init__.py` is metadata-only
For all packages under `dare_framework/**/__init__.py`:
- Keep only a package-level docstring (and optionally comments for intent).
- Allow metadata constants (e.g., `__version__`).
- No `class` / `def` statements; no imports or re-exports.

Rationale:
- Makes package boundaries obvious and keeps files “clean”.
- Forces module-of-definition imports, reducing ambiguity about symbol ownership.

### 2) “Contracts live in modules, not in `__init__.py`” (Kernel domains)
For each affected Kernel domain package, split contract definitions into:
- `models.py`: dataclasses, enums, and simple value objects.
- `protocols.py`: `Protocol` interfaces (Kernel contract surfaces).
- `errors.py`: domain exceptions (only when a domain has them).
- `__init__.py`: docstring + metadata only.

### 3) Remove pass-through re-export modules
If a file exists only to forward symbols (e.g., `components/*/protocols.py` that simply imports a contract
from `contracts/`), remove it and update call sites to import from the canonical module-of-definition.

### 4) Target module map
This is the target direction; exact filenames can be finalized in apply stage.

```
dare_framework/core/budget/
  __init__.py
  models.py        # ResourceType, Budget
  errors.py        # ResourceExhausted
  protocols.py     # IResourceManager
  in_memory.py     # InMemoryResourceManager (default impl)

dare_framework/core/context/
  __init__.py
  models.py        # ContextStage, AssembledContext, Prompt, ...
  protocols.py     # IContextManager
  default_context_manager.py

dare_framework/core/event/
  __init__.py
  models.py        # Event, RuntimeSnapshot
  protocols.py     # IEventLog
  local_event_log.py

dare_framework/core/execution_control/
  __init__.py
  models.py        # ExecutionSignal
  errors.py        # PauseRequested, CancelRequested, HumanApprovalRequired
  protocols.py     # IExecutionControl
  checkpoint.py
  file_execution_control.py

dare_framework/core/hook/
  __init__.py
  models.py        # HookPhase
  protocols.py     # IExtensionPoint
  default_extension_point.py

dare_framework/core/orchestrator/
  __init__.py
  protocols.py     # ILoopOrchestrator
  default_orchestrator.py

dare_framework/core/run_loop/
  __init__.py
  models.py        # RunLoopState, TickResult
  protocols.py     # IRunLoop
  default_run_loop.py

dare_framework/core/security/
  __init__.py
  models.py        # PolicyDecision, TrustedInput, SandboxSpec
  protocols.py     # ISecurityBoundary
  default_security_boundary.py
```

## Risks / Trade-offs
- Import cycles: splitting files can introduce accidental cycles. Mitigation: keep `models.py` dependency-light,
  keep `Protocol` definitions in `protocols.py`, and rely on `from __future__ import annotations` +
  forward references where needed.
- Increased import verbosity: removing `__init__.py` re-exports makes imports longer. This is intentional
  (compatibility is out of scope) and trades brevity for clarity and refactor-safety.

## Validation Plan
- Structural check: unit test ensures `__init__.py` contains no class/def and no imports.
- Unit tests: `pytest` (targeted to imports first, then full suite).
- Static checks: `ruff`, `black --check`, `mypy --strict`.
