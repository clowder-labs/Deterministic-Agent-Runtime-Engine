# Change: Add basic chat flow with prompts, OpenAI adapter, and interactive stdio tracing

## Why
We need a minimal, usable chat flow that exercises the core framework loops without premature complexity. This enables a first agent client (stdin/stdout), a base prompt, an OpenAI adapter via LangChain, and readable hook output for terminal debugging while keeping other plugins as no-op.

## What Changes
- Add a default English base system prompt stored in the default prompt store.
- Introduce an OpenAI model adapter built on `langchain-openai` and wired into the runtime loop.
- Provide a local command tool with workspace root restrictions for write operations.
- Add an interactive stdin/stdout chat example that loops until `/quit`, preserves session context across turns, and prints model responses.
- Add a stdout hook that renders plan/model/tool events for human-readable tracing.
- Dispatch runtime events to configured hooks and include plan, model response, and tool result details.
- Extend runtime/config plumbing so tools can access `workspace_roots` from session config.
- Keep LLM adapter configuration as code placeholders in the example (no config-file loading yet).
- Add a root dependency manifest to install runtime and test dependencies consistently.

## Impact
- Affected modules: `dare_framework/core`, `dare_framework/components`, `dare_framework/composition`, `examples/`.
- New dependency: `langchain-openai` (and its `langchain-core` dependency).
- No backward-compat requirement (early-stage framework).
