## Context

The canonical context implementation currently assembles model input from STM only. Although `Context` already carries `long_term_memory` and `knowledge`, the default assembly path ignores both, so cross-session memory and external knowledge are unavailable unless users override assembly manually.

This change delivers a baseline fusion strategy directly in `DefaultAssembledContext` with explicit budget-aware degradation semantics. It keeps API signatures stable (`Context.assemble() -> AssembledContext`) and uses conservative defaults to preserve backward compatibility.

## Goals / Non-Goals

**Goals:**
- Include LTM/Knowledge retrieval in default context assembly.
- Derive retrieval query from latest user intent in STM.
- Apply budget-aware degradation before adding retrieval results.
- Emit retrieval metadata in assembled output for auditability.

**Non-Goals:**
- No full tokenization model integration (use lightweight token estimation heuristic).
- No change to `IContext`/`IRetrievalContext` method signatures.
- No new external dependency.

## Decisions

### Decision 1: Query derivation from latest user message

- Use latest STM message with role `user` as retrieval query.
- Fallback to latest non-empty STM content, else empty query.

Rationale:
- Aligns retrieval intent with current user instruction while avoiding interface changes.

### Decision 2: Budgeted retrieval window with deterministic degradation

- Compute `remaining_tokens = context.budget_remaining("tokens")`.
- Estimate token usage by content length heuristic (roughly `len(content) // 4 + overhead`).
- Reserve a minimum token buffer (`reserve_tokens`, default 256).
- If remaining budget after STM+reserve is non-positive, skip retrieval and mark degradation reason.
- Otherwise split retrieval budget by source ratios (default: LTM 50%, Knowledge 50%) and include messages until each source budget is exhausted.

Rationale:
- Ensures baseline behavior remains safe under constrained budgets without requiring expensive tokenizer calls.

### Decision 3: Minimal configurable knobs through existing Config dictionaries

- Read optional keys from existing config dictionaries:
  - `config.long_term_memory`: `assemble_top_k`, `assemble_ratio`
  - `config.knowledge`: `assemble_top_k`, `assemble_ratio`
  - `config.long_term_memory` fallback key `assemble_reserve_tokens`
- Defaults apply when keys are absent/invalid.

Rationale:
- Avoids config schema expansion while enabling practical tuning.

### Decision 4: Retrieval metadata is explicit and stable

- Add `metadata["retrieval"]` with:
  - `query`, `stm_count`, `ltm_count`, `knowledge_count`
  - `ltm_requested`, `knowledge_requested`
  - `degraded` and optional `degrade_reason`

Rationale:
- Supports observability and future policy/debugging without changing message schema.

## Risks / Trade-offs

- [Risk] Heuristic token estimation may differ from model tokenizer reality.  
  -> Mitigation: keep conservative reserve and deterministic clipping.

- [Risk] Retrieval implementations vary (vector/rawdata), so query quality may differ.  
  -> Mitigation: keep source-agnostic fallback and strict failure isolation.

- [Risk] Retrieval exceptions could break assembly.
  -> Mitigation: catch retrieval exceptions and degrade that source only.

## Migration Plan

1. Add fusion + degradation logic in `DefaultAssembledContext`.
2. Add unit tests for query derivation, source fusion, and degradation behavior.
3. Run targeted context + agent smoke regressions.
4. Update DG-006 TODO evidence after verification.

Rollback:
- Revert to STM-only assemble path; no API rollback required.

## Open Questions

- Should we promote `assemble_*` keys to first-class config types in a later change?
- Do we need per-source hard minimum quotas (e.g., always keep at least 1 knowledge item)?
