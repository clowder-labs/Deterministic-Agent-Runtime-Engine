## Context
Specs already define a prompt store concept (`IPromptStore`) and require a default base system prompt to be exposed to context assembly. The current runtime does not yet:
- provide a prompt store implementation,
- support external (workspace/user) prompt overrides,
- or resolve model-aware prompt variants during agent initialization.

This change introduces a small, deterministic prompt management layer that satisfies those needs without forcing async context assembly.

## Goals / Non-Goals
- Goals:
  - Provide a default layered prompt store that can load built-in prompts and external prompt manifests.
  - Allow model-aware prompt selection while keeping prompt IDs stable.
  - Make agent initialization resolve prompt information from the selected model adapter.
  - Keep prompt resolution deterministic and auditable (clear lookup order, clear fallbacks).
  - Support explicit prompt overrides via builder/config without breaking deterministic selection.
- Non-Goals:
  - A full prompt DSL, templating engine, or dynamic runtime prompt mutation.
  - Remote prompt fetching (HTTP) or database-backed prompt stores (can be future work via pluggable stores).
  - Multi-stage (plan/execute/verify) prompt packs beyond defining the shape and the base system prompt path.

## Decisions
- Model request payload is named `ModelInput` (renamed from `Prompt`) to avoid ambiguity with stored Prompt definitions.
- `IModelAdapter` is treated as a stable kernel contract and lives in `model/kernel.py` (manager stays in `model/interfaces.py`).
- Prompt IDs are stable strings (e.g., `base.system`).
- Prompts include `prompt_id`, `role`, `content`, `supported_models`, `order`, and optional `version`.
  - `supported_models` is a list of model identity strings; `*` matches any model.
  - `order` is an integer priority; higher wins.
- Prompt loaders are a public interface (`IPromptLoader`) that returns prompts and preserves stable source order.
- Prompt sources load from deterministic locations using a single manifest path pattern:
  - Config: `prompt_store_path_pattern` (default `.dare/_prompts.json`)
  - User: `<user_dir>/<prompt_store_path_pattern>`
  - Workspace: `<workspace_dir>/<prompt_store_path_pattern>`
  - Precedence: workspace > user > built-in
- Prompt resolution by model identity:
  - The model identity is `IModelAdapter.name`.
  - For a given `prompt_id`, select the highest `order` prompt whose `supported_models` includes the model identity or `*`.
  - If multiple prompts share the same `order`, break ties by source precedence (workspace > user > built-in), then by stable source order.
- Prompt selection precedence:
  1) Explicit prompt override from the builder
  2) Explicit `prompt_id` override from the builder
  3) Config `default_prompt_id`
  4) Model-aware selection from the prompt store
- Built-in `base.system` MUST include `supported_models: ["*"]` with the lowest `order`.

### Prompt Manifest Schema
- File shape: `{ "prompts": [ ... ] }`
- Each prompt entry:
  - `prompt_id` (string, required)
  - `role` (string, required; aligns with `Message.role`)
  - `content` (string, required)
  - `supported_models` (list[string], required; may include `*`)
  - `order` (int, required; higher is preferred)
  - `version` (string, optional)
  - `name` (string, optional)
  - `metadata` (object, optional)

### Prompt Manifest Sketch
```json
{
  "prompts": [
    {
      "prompt_id": "base.system",
      "role": "system",
      "content": "You are a deterministic agent runtime...",
      "supported_models": ["*"],
      "order": 0
    }
  ]
}
```

## Open Questions
- Which prompt "roles" should be part of the initial prompt profile (only `base.system`, or also planner/validator system prompts)?
