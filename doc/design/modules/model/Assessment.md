# Model Domain Assessment

> Status: draft (2026-02-03). Scope: `dare_framework/model` only.

## 1. Scope & Responsibilities

- Provide the core `IModelAdapter` contract for LLM invocation.
- Define model I/O types (`ModelInput`, `ModelResponse`, `GenerateOptions`, `Prompt`).
- Provide prompt loading and resolution contracts.
- Supply default adapters and prompt stores via explicit defaults.

## 2. Current Public Surface (Facade)

`dare_framework.model` exports:
- Interfaces: `IModelAdapter`, `IModelAdapterManager`, `IPromptLoader`, `IPromptStore`
- Types: `Prompt`, `ModelInput`, `ModelResponse`, `GenerateOptions`
- Factories: `create_default_model_adapter_manager`, `create_default_prompt_store`
- Default implementations: adapters + prompt loaders/stores

## 3. Actual Dependencies

- **Config**: `Config.llm` controls adapter selection and prompt store paths.
- **Context**: `ModelInput.messages` uses `context.Message`.
- **Tool**: tool definitions are passed through `ModelInput.tools`.
- **Agent**: agents call `IModelAdapter.generate()` and feed the results into tool loops.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Default implementations exposed**
   - Adapters and prompt loaders are exported from the facade for convenience.

2. **Tool schema normalization is implicit**
   - Adapters normalize tool defs for OpenAI format, but the schema is not documented.

3. **Client typing is loose**
   - Adapters keep `Any` clients; a minimal protocol could clarify expectations.

## 5. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.model`**:
  - `IModelAdapter`, `IModelAdapterManager`, `IPromptLoader`, `IPromptStore`
  - `Prompt`, `ModelInput`, `ModelResponse`, `GenerateOptions`
  - Factories: `create_default_model_adapter_manager`, `create_default_prompt_store`
  - `OpenAIModelAdapter`, `OpenRouterModelAdapter`
  - `BuiltInPromptLoader`, `FileSystemPromptLoader`, `LayeredPromptStore`
  - `DefaultModelAdapterManager`

## 6. Doc Updates Needed

- `doc/design/modules/model/README.md`: clarify defaults namespace.
- `doc/design/modules/model/Model_Prompt_Management.md`: reference defaults for loaders/store.
- `doc/design/Framework_MinSurface_Review.md`: align surface notes.

## 7. Proposed Implementation Plan (Model Domain)

1. Keep default implementations in the model facade for ease of use.
2. Keep factories as the preferred entry points.
3. Ensure docs/tests reference the top-level modules.

## 8. Open Questions

- Should the tool schema be formalized (e.g., canonical ToolDefinition)?
- Do we need a typed prompt store reload interface?
