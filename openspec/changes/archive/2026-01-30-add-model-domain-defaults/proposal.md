# Change: Add model domain defaults and public factories

## Why
The model domain lacks a default `IModelAdapterManager` implementation, forcing external modules to reach into `_internal/` for default behavior. This violates the architecture rule that `_internal/` is not a public API and should not be imported across domains. We also want to move the OpenRouter model adapter from the five-layer example into the model domain so it is a first-class adapter.

## What Changes
- Add a default `IModelAdapterManager` implementation that resolves adapters from `Config.llm` and falls back to `OpenAIModelAdapter`.
- Provide public factory functions in the model domain for default prompt store and default model adapter manager, and update builders to use those factories instead of importing `_internal/`.
- Move the OpenRouter model adapter into the model domain and update examples to import it from `dare_framework.model`.
- Update architecture documentation to clarify that `_internal/` is not accessed by other domains and that factories are the supported entry points.

## Impact
- Affected specs: `interface-layer`, `prompt-store`, `organize-layered-structure`, `model-adapter-openrouter` (new)
- Affected code: `dare_framework/model/*`, `dare_framework/builder/*`, `examples/five-layer-coding-agent/*`, and related docs/tests.
