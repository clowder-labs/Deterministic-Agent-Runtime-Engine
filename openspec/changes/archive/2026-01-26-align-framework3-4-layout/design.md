## Context
v4.0 docs define a domain layout convention (`types.py` + `kernel.py` + optional `interfaces.py` + optional `_internal/`) and call out `dare_framework3_4` as the baseline for the "context-centric" direction (request-time assembly via `Context.assemble()`).

Today, `dare_framework3_4/` is:
- Minimal (only agent/context/model/tool/memory/knowledge).
- Not following the v4.0 domain file naming convention.
- Partially inconsistent/incomplete (e.g., `tool/internal/__init__.py` imports modules that only exist in `dare_framework3_3/`).

This change focuses on alignment at the *interface and layout level* (Protocols, type models, and package structure), keeping implementation minimal.

## Goals / Non-Goals
- Goals:
  - Make `dare_framework3_4/` structure match the v4.0 domain layout convention as closely as possible.
  - Provide interface declarations consistent with `docs/design/Interfaces.md` (agent/context/tool + placeholders for plan/security/event/hook/config).
  - Migrate legacy `internal/` packages to `_internal/`.
  - Ensure all placeholder domains are importable (even without implementations).
- Non-Goals:
  - Fully implement v4.0 runtime semantics inside `dare_framework3_4/` (planning, policy, event log, sandboxing).
  - Refactor/replace the canonical `dare_framework/` package (this proposal is scoped to the historical v3.4 directory).

## Decisions
- Decision: Do not preserve legacy import paths.
  - Rationale: The goal is doc-alignment, not backwards compatibility for historical v3.4 module paths.
- Decision: Rename `internal/` → `_internal/` across `dare_framework3_4/`.
  - Rationale: Matches the v4.0 domain convention and avoids ambiguity about what is public API.
- Decision: Add placeholder domains for `plan`, `security`, `event`, `hook`, and `config`.
  - Rationale: `docs/design/Interfaces.md` describes these domains as part of the target interface surface; placeholders allow early alignment without committing to runtime behavior.
- Decision: Fix `tool._internal` exports by making the package import-safe first, then adding implementations only when explicitly requested.
  - Rationale: Alignment work should not introduce broken imports.

## Risks / Trade-offs
- Breakage risk: renaming/moving modules will require updating all internal imports (and any examples/docs that import v3.4 directly).
  - Mitigation: keep the change scoped to v3.4-only paths and add compile/import validation.
- Scope creep risk: v4.0 contains many domains (plan/security/event/hook/config) that v3.4 did not implement.
  - Mitigation: add placeholder interfaces only; do not implement behavior unless requested.

## Open Questions
- None.
