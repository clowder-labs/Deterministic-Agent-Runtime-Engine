# Change: Refactor plugin system + remove legacy v1 surfaces (v2)

## Why
The framework has moved to the v2 Kernel architecture (`doc/design/Architecture_Final_Review_v2.0.md`), but there are still two gaps that prevent the project from being “v2 clean”:

1) HITL requires an explicit “waiting” control-plane call (even if the MVP implementation does not truly block).
2) The framework’s extension mechanism is entrypoint-based, but the current entrypoint groups/managers are v1-shaped and the v2 runtime still depends on many `dare_framework/core/*` legacy contracts/types.

This change removes v1-only contracts/implementations, migrates the remaining shared types into v2-aligned locations, and upgrades the entrypoint/plugin loading path so v2 composition remains the default and verification examples can be adapted (not deleted).

## What Changes
- Add an explicit HITL waiting surface to `IExecutionControl`:
  - `wait_for_human(checkpoint_id, reason)` MUST be called for `APPROVE_REQUIRED` decisions.
  - MVP MAY be non-blocking (records WORM evidence and returns), but the interface must exist and be wired.
- Refactor entrypoint-based plugin loading to be v2-native:
  - Introduce **new v2 entrypoint groups** (no compatibility with v1 groups required).
  - Provide v2 component manager **interfaces** (and no-op defaults) for all entrypoint-extensible categories, with docstrings/comments that clearly state the intended behavior and design goals.
  - Manager-driven loading rules (config-driven selection/filtering) are defined as part of the interface contract and documentation:
    - `model_adapter` is selected by configured name.
    - `validators` load as an ordered, config-filtered set (returned as a collection).
    - Other component categories follow their manager-defined rules (single-select vs multi-load), but MAY remain no-op initially.
- Remove or migrate legacy v1 surfaces:
  - Migrate shared “still-needed” types currently living under `dare_framework/core/*` into v2-aligned modules.
  - Remove v1-only protocols/implementations (e.g., `IContextAssembler`, `IToolRuntime`, `ICheckpoint`, `IPolicyEngine`, v1 plan generator) and their default implementations once all callers are migrated.
- Adapt verification code (examples/tests) to the updated v2 contracts:
  - Do **not** delete `examples/coding-agent/openai_adapter.py` and `examples/coding-agent/real_model_agent.py`; update them after the main framework flow is finalized.

## Impact
- Affected specs: `core-runtime` (execution control), `plugin-system` (entrypoints + config rules), `interface-layer` (remove v1 contracts), `example-agent` (examples as verification).
- Affected code: `dare_framework/core/*`, `dare_framework/builder.py`, plugin/entrypoint managers, `examples/*`, `tests/*`.
- **BREAKING**: new entrypoint group names; removal/migration of legacy v1 import paths.

## References
- `doc/design/Architecture_Final_Review_v2.0.md` (authoritative)
- `doc/guides/Development_Constraints.md` (implementation constraints)
