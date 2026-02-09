# DARE Framework Domain Assessment (2026-02-03)

## 1. Scope and Method
This assessment reviews the current `dare_framework/` domains against the
existing design docs under `docs/design/modules/` and `docs/design/Interfaces.md`.
It focuses on:
- Domain responsibilities and boundaries (kernel/interfaces/types vs _internal)
- Type correctness and API signatures (forward refs, `Any`, return types)
- Import layering and dependency clarity
- Implementation clarity vs documented intent

## 2. Issue Classification
- **Doc gap**: design docs are missing or unclear for current behavior.
- **Impl gap**: implementation deviates from the documented design.
- **Both**: both doc and implementation are unclear or inconsistent.

## 3. Cross-cutting Findings
1. **Type annotations are inconsistent**
   - Many modules still use string annotations even with
     `from __future__ import annotations` enabled.
   - Impact: lower static type signal, unnecessary forward refs, harder refactors.
   - Fix: prefer real types + `TYPE_CHECKING` imports; reserve string refs only
     for unavoidable circular runtime imports.

2. **Return types are too loose (`Any`) in public APIs**
   - Examples: `dare_framework/agent/_internal/builder.py:build()` returns `Any`;
     `dare_framework/tool/kernel.py:IToolGateway.invoke()` returns `Any`.
   - Impact: API contract unclear; violates kernel stability intent.
   - Fix: tighten signatures to domain types (`DareAgent`, `ToolResult`, etc.).

3. **Domain boundary conventions are uneven**
   - Some domains lack `kernel.py` (embedding, skill), while others keep empty
     kernels (plan).
   - Impact: unclear API stability surface; inconsistent with
     `docs/design/Interfaces.md` structure rules.
   - Fix: introduce missing kernels or explicitly document why interfaces-only.

4. **Design docs lag behind implementation**
   - Example: agent hooks are now emitted but module doc still says they are not.
   - Impact: onboarding confusion, incorrect assumptions for integrators.
   - Fix: refresh per-domain docs to match actual behavior and highlight TODOs.

## 4. Per-domain Assessment

### 4.1 Agent
**Responsibilities**: orchestrate runtime execution, coordinate plan/tool/model,
expose minimal `IAgent.run(...)` surface.

**Key APIs**: `dare_framework/agent/kernel.py`,
`dare_framework/agent/five_layer.py`,
`dare_framework/agent/builder.py`.

**Findings**
- **Resolved**: builder `build()` now returns typed agent per builder.
- **Resolved**: transport loop is internal (`_run_transport_loop`).
- **Resolved**: module doc updated to reflect hook emissions.

**Recommended changes**
- Keep builders typed per agent and keep transport lifecycle internal.

### 4.2 Config
**Responsibilities**: config model, layered loading, component toggles.

**Key APIs**: `dare_framework/config/types.py`, `kernel.py`.

**Findings**
- **Impl gap**: `component_config()` returns `Any` (no schema), hard to consume
  safely.
- **Doc gap**: config schema for component-specific configs not defined.

**Recommended changes**
- Define a typed component config schema (even if `dict[str, Any]`).
- Document config resolution/shape more precisely in module docs.

### 4.3 Context
**Responsibilities**: assemble request-time messages/tools; host STM/LTM/knowledge.

**Key APIs**: `dare_framework/context/kernel.py`, `_internal/context.py`.

**Findings**
- **Impl gap**: `Context` stores skill state (`current_skill`) but doc does not
  mention skill integration.
- **Type issue**: several fields use string annotations (`Prompt`,
  `IToolProvider/IToolManager`), redundant with `__future__` annotations.

**Recommended changes**
- Clarify skill injection path (Context vs Agent) and document it.
- Replace string type annotations with direct types + `TYPE_CHECKING` imports.

### 4.4 Embedding
**Responsibilities**: provide embedding adapters for knowledge retrieval.

**Key APIs**: `dare_framework/embedding/interfaces.py`, `types.py`.

**Findings**
- **Doc/Impl gap**: no `kernel.py` despite kernel conventions in
  `docs/design/Interfaces.md`.
- **Type issue**: adapter client helpers return `Any` in `_internal`.

**Recommended changes**
- Add `embedding/kernel.py` with stable `IEmbeddingAdapter` contract, or
  document why interfaces-only.
- Define minimal adapter client type or alias to reduce `Any`.

### 4.5 Event
**Responsibilities**: WORM audit log, query, replay.

**Key APIs**: `dare_framework/event/kernel.py`, `types.py`.

**Findings**
- **Doc/Impl gap**: only interfaces exist; legacy `dare_framework/events/*`
  event bus still present without migration plan.

**Recommended changes**
- Define a migration policy: deprecate legacy event bus or map it to
  `IEventLog`.
- Add a minimal default EventLog implementation or an explicit placeholder
  contract in docs.

### 4.6 Hook
**Responsibilities**: lifecycle hooks, best-effort extension points.

**Key APIs**: `dare_framework/hook/kernel.py`, `interfaces.py`.

**Findings**
- **Doc gap**: payload schema expectations are not captured, while observability
  assumes certain fields.

**Recommended changes**
- Define minimal hook payload schemas per phase in docs.
- Document error handling contract (best-effort, non-fatal).

### 4.7 Memory / Knowledge
**Responsibilities**: retrieval contexts for STM/LTM/knowledge; provide default
implementations.

**Key APIs**: `dare_framework/memory/kernel.py`, `dare_framework/knowledge/kernel.py`,
`dare_framework/memory/factory.py`, `dare_framework/knowledge/factory.py`.

**Findings**
- **Doc gap**: module doc is combined, but code is split into two domains with
  separate factories and types.
- **Type issue**: string annotations for `Message` and `IEmbeddingAdapter` in
  factories.

**Recommended changes**
- Clarify whether memory/knowledge are separate domains or a unified module.
- Document factory selection logic and embedding adapter dependency.
- Replace string annotations with concrete types + `TYPE_CHECKING` imports.

### 4.8 Model
**Responsibilities**: model adapter abstraction, prompt store/loading.

**Key APIs**: `dare_framework/model/kernel.py`, `interfaces.py`,
`_internal/openai_adapter.py`.

**Findings**
- **Impl gap**: adapter client creation returns `Any` (no stable client type).
- **Doc gap**: tool definition schema normalization not fully specified.

**Recommended changes**
- Introduce a minimal `ModelClient` protocol or type alias to replace `Any`.
- Document the expected tool definition schema in model module docs.

### 4.9 Observability
**Responsibilities**: OTel traces/metrics/logs, hook-driven measurement.

**Key APIs**: `dare_framework/observability/kernel.py`, `_internal/*`.

**Findings**
- **Doc gap**: hook payload contract is assumed but not enforced globally.

**Recommended changes**
- Align hook payload schema across agent/tool/model modules (doc contract).

### 4.10 Plan
**Responsibilities**: plan types + planner/validator/remediator strategies.

**Key APIs**: `dare_framework/plan/types.py`, `interfaces.py`.

**Findings**
- **Doc/Impl gap**: `plan/kernel.py` is empty, despite kernel convention.
- **Type issue**: several internal validators accept/return `Any` for ctx or
  plan types.

**Recommended changes**
- Move stable contracts into `plan/kernel.py` or document why none.
- Tighten internal validator signatures to `ProposedPlan/ValidatedPlan`.

### 4.11 Security
**Responsibilities**: trust derivation, policy checks, sandbox execution.

**Key APIs**: `dare_framework/security/kernel.py`, `types.py`.

**Findings**
- **Doc/Impl gap**: only interfaces exist; no default implementation or
  integration into agent/tool loops.

**Recommended changes**
- Add a no-op or stub security boundary with explicit policy contract.
- Document integration points for tool invocation and plan validation.

### 4.12 Skill
**Responsibilities**: skill loading, selection, execution as tools.

**Key APIs**: `dare_framework/skill/interfaces.py`, `_internal/*`.

**Findings**
- **Doc/Impl gap**: no `skill/kernel.py`; skill usage path in Context/Agent is
  ambiguous in docs.

**Recommended changes**
- Add `skill/kernel.py` or explicitly note interfaces-only domain.
- Document how skills are injected into prompts or context.

### 4.13 Tool
**Responsibilities**: trusted capability registry + execution gateway.

**Key APIs**: `dare_framework/tool/kernel.py`, `interfaces.py`,
`tool/default_tool_manager.py`.

**Findings**
- **Impl gap**: `IToolGateway.invoke()` returns `Any` but should return
  `ToolResult` per tool model contract.
- **Type issue**: forward refs used for `ITool`/`IToolProvider` with string
  annotations despite `__future__` annotations.

**Recommended changes**
- Tighten `invoke()` signature to `ToolResult` and propagate to callers.
- Replace string annotations with direct types + `TYPE_CHECKING` imports.

### 4.14 Transport
**Responsibilities**: agent↔client interaction envelopes and channels.

**Key APIs**: `dare_framework/transport/kernel.py`, `types.py`,
`_internal/default_channel.py`.

**Findings**
- **Doc gap**: lifecycle and encoder/decoder usage must be clearly stated in
  module design (now addressed in `transport_mvp.md`).

**Recommended changes**
- Keep transport lifecycle documented in module design docs and examples.

## 5. Proposed Execution Plan (Domain-by-domain)
1. **Baseline type contract cleanup**
   - Replace string annotations with real types in kernel/interfaces.
   - Tighten return types (`ToolResult`, concrete agent builders).
2. **Domain boundary normalization**
   - Add missing kernels (embedding/skill), or formally declare interfaces-only.
3. **Doc alignment pass**
   - Update module design docs and `docs/design/Interfaces.md` to match reality.
4. **Behavioral refactors by domain**
   - Agent: lifecycle and transport loop isolation.
   - Tool: enforce `ToolResult` path and policy hooks.
   - Security/Event: add default stubs and clarify integration points.
