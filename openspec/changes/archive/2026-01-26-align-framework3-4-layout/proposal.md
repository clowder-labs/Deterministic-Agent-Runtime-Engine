# Change: Align `dare_framework3_4` layout and interface declarations to v4.0 docs

## Why
`dare_framework3_4/` is referenced as evidence for the v4.0 "context-centric" direction, but its current domain layout and interface surfaces drift from the v4.0 design docs (`doc/design/Architecture.md` + `doc/design/Interfaces.md`). This makes review and migration harder, and some modules are currently incomplete (e.g., `dare_framework3_4/tool/internal/__init__.py` imports non-existent modules).

## What Changes
- Add v4.0 doc-aligned domain scaffolding to `dare_framework3_4/`:
  - Per-domain `types.py`, `kernel.py`, `interfaces.py` (optional), and `_internal/` (optional).
- Add missing interface declarations referenced by the v4.0 docs (Protocols + types), without prematurely implementing full behavior.
- Rename legacy `internal/` packages to `_internal/` to match the v4.0 domain convention.
- Add placeholder domains referenced by v4.0 docs (plan/security/event/hook/config) with minimal types + Protocol declarations.
- Fix obviously broken imports in `dare_framework3_4/tool/internal/__init__.py` by removing or replacing invalid exports as part of the `internal/` → `_internal/` migration.
- Update `doc/design/DARE_evidence.yaml` source paths if this change moves any evidence-referenced v3.4 files.

## Impact
- Affected code: `dare_framework3_4/` (directory structure + interface declarations; may change module paths).
- Affected docs: `doc/design/DARE_evidence.yaml` (may require path updates to keep evidence valid).
- Affected specs: new delta spec `framework3-4-layout` (proposal-level; implementation later).
