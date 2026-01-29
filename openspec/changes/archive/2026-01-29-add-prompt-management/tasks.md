## 1. Implementation
- [x] 1.1 Rename runtime Prompt to `ModelInput` and update model adapter signatures/usages.
- [x] 1.2 Move `IModelAdapter` to `model/kernel.py` and keep `IModelAdapterManager` in `model/interfaces.py`.
- [x] 1.3 Add prompt domain types (Prompt with `supported_models` + `order`) + `IPromptStore` interface.
- [x] 1.4 Add public `IPromptLoader` interface and implement built-in + filesystem loaders.
- [x] 1.5 Implement a default layered prompt store using prompt manifests (built-in + user/workspace via `prompt_store_path_pattern`).
- [x] 1.6 Implement model-aware prompt resolution (match `supported_models`, select highest `order`, fallback to `*`).
- [x] 1.7 Update context assembly to prepend the resolved base system prompt deterministically (respect explicit prompt overrides).
- [x] 1.8 Update agent builders to support explicit Prompt or `prompt_id` overrides and config `default_prompt_id`.
- [x] 1.9 Update `examples/basic-chat/*` to use the prompt store and document override behavior.
- [x] 1.10 Add unit tests for prompt lookup precedence, `order` resolution, and wildcard fallback.

## 2. Validation
- [x] 2.1 Run unit tests for prompt store + context assembly.
- [ ] 2.2 Manual smoke run of the basic chat example with an overridden `base.system` prompt.
