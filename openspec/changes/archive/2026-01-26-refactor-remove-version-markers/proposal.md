# Change: Remove version markers from active code, tests, and docs

## Why
The canonical `dare_framework` package is now the single source of truth. Versioned labels in filenames, docstrings, and documentation (e.g., numeric version suffixes) add confusion and undermine the goal of maintaining a single, final codebase and documentation set.

## What Changes
- Rename active example/test files that include version suffixes to neutral, descriptive names.
- Remove version-specific labels from docstrings, logs, comments, and non-archived documentation.
- Update imports and references accordingly.
- Leave archived code and archived documents untouched under `archive/`.

## Impact
- Affected specs: `organize-layered-structure`
- Affected code: `dare_framework/**`, `examples/**`, `tests/**`, `docs/design/**` (non-archive)

## Open Questions
- Naming collisions: confirm target filenames for basic-chat scripts and config tests since some neutral names already exist.
- Should we consolidate duplicate basic-chat scripts into a single canonical example, or keep multiple renamed variants?
