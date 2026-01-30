## Context
The current builder uses prompt store implementations from `model/_internal` directly. The architecture docs state `_internal/` is not public, so cross-domain imports should go through domain-level APIs. The model domain also lacks a default `IModelAdapterManager`, forcing external wiring to supply one even for common OpenAI usage. Additionally, the OpenRouter adapter lives under an example-specific folder, which makes it difficult to reuse and contradicts the domain ownership rules.

## Goals / Non-Goals
Goals:
- Provide a default `IModelAdapterManager` for common OpenAI usage, configured via `Config.llm`.
- Expose public factory functions in the model domain so other domains do not import `_internal/` directly.
- Move the OpenRouter model adapter into the model domain and expose it through the model facade.
- Align architecture docs with the intended boundaries.

Non-Goals:
- Entry point discovery for model adapters (deferred to a later proposal).
- Changing the builder precedence rules (explicit injection still wins).
- Adding new prompt sources or changing prompt selection semantics.

## Decisions
1) **Default model adapter manager**
   - Provide a minimal built-in implementation (no entrypoints) that reads `Config.llm`.
   - Precedence: explicit builder injection > manager resolution via `config.llm.adapter` > default OpenAI adapter.
   - If `config.llm.adapter` is set to an unsupported value, raise a descriptive error.
   - Adapter configuration uses all relevant `Config.llm` fields (not just `model`).

2) **Public factory functions**
   - Introduce `model/factories.py` with `create_default_model_adapter_manager(config)` and `create_default_prompt_store(config)`.
   - Re-export factories from `dare_framework.model.__init__` so external domains do not import `_internal/`.
   - Builders will call these factories when no explicit manager/store is provided.

3) **OpenRouter adapter migration**
   - Move the OpenRouter adapter from `examples/five-layer-coding-agent/model_adapters/` into `dare_framework/model/_internal/`.
   - Expose `OpenRouterModelAdapter` via `dare_framework.model` public facade.
   - Update the adapter to implement `IModelAdapter` and accept `ModelInput` (consistent with the model domain).

## Risks / Trade-offs
- Moving the OpenRouter adapter changes import paths for examples; docs/tests must be updated.
- The default manager behavior becomes part of the public contract; errors for unknown adapters must be explicit and stable.

## Migration Plan
1) Add factories and default manager in model domain.
2) Update builder to use factories instead of `_internal` imports.
3) Move OpenRouter adapter and update example imports.
4) Update docs and tests.

## Open Questions
- None (entrypoint discovery is explicitly deferred).
