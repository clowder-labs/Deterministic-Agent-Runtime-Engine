# Change: Add prompt management + model-adapter prompt mapping

## Why
The runtime currently builds prompts only from short-term memory messages and does not have a first-class prompt management mechanism. This blocks a few design goals that are already captured in specs and historical design docs:

- A default base system prompt should be provided via an `IPromptStore` and be injected into context assembly.
- Prompts should be loadable from both built-in defaults and external sources (workspace/user overrides).
- Different `IModelAdapter` implementations should be able to select the best prompt variant deterministically (including explicit overrides) without forking agent logic.

## What Changes
- Define the prompt domain surface (`IPromptStore` + Prompt types) and a default layered prompt store implementation.
- Introduce a manifest-driven prompt loader (`prompt_store_path_pattern`, default `.dare/_prompts.json`) with workspace/user/built-in precedence.
- Add deterministic prompt resolution rules using `supported_models` + `order`, including wildcard fallback and explicit overrides.
- Allow builders/config to override prompt selection via `Prompt` or `prompt_id` (with a single effective override).
- Rename runtime prompt input to `ModelInput` and move `IModelAdapter` to `model/kernel.py` to align stable interface ownership.
- Ensure agents resolve prompt information during initialization (based on the configured model adapter) and feed it into context assembly.
- Update examples/tests to cover prompt loading, overrides, and model-aware prompt selection order.

## Impact
- Affected specs: `prompt-store`, `prompt-baseline` (+ new `prompt-management` capability).
- Affected code (planned): `dare_framework/model/*`, `dare_framework/context/*`, `dare_framework/builder/*`, `examples/basic-chat/*`, prompt-related tests.
