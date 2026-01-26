# Change: Archive legacy frameworks and promote v3.4 as dare_framework

## Why
The repository keeps multiple historical framework packages at the root, which creates ambiguous imports and splits attention across versions. We need a single canonical package for active development while preserving old code for reference.

## What Changes
- Move legacy framework directories (`dare_framework`, `dare_framework2`, `dare_framework3`, `dare_framework3_2`, `dare_framework3_3`) into an archive root (`archive/frameworks/`) so they are no longer top-level importable packages but remain available for reference.
- Rename `dare_framework3_4/` to `dare_framework/` and update module paths/imports across code, examples, tests, and docs.
- Update examples/tests that referenced legacy versions to target the canonical package where feasible; otherwise document missing APIs needed to make them runnable.
- Add brief archive documentation to explain the legacy location and usage expectations.

## Impact
- Affected specs: `organize-layered-structure`
- Affected code: repository root framework packages, `examples/`, `tests/`, and any docs referencing old package names.

## Open Questions
- Confirm the archive location `archive/frameworks/`.
