## 1. Implementation
- [x] 1.1 Add `Config.workspace_roots` and propagate session config into `RunContext` for tool access.
- [x] 1.2 Add a prompt-aware context assembler and seed the default `InMemoryPromptStore` with the base English system prompt.
- [x] 1.3 Implement `OpenAIModelAdapter` using `langchain-openai`, mapping messages and tool calls to `ModelResponse`.
- [x] 1.4 Update `AgentRuntime` execute loop to call the model adapter, run tool calls via `ToolRuntime`, and emit a final response output.
- [x] 1.5 Implement `RunCommandTool` with workspace root enforcement and basic timeout handling.
- [x] 1.6 Dispatch runtime events to hooks and emit plan/model/tool detail events (including hook error events) for tracing.
- [x] 1.7 Add a stdout hook that prints human-readable summaries (non-fatal on hook errors).
- [x] 1.8 Update the stdin/stdout chat example to loop until `/quit`, preserve session context across turns, read raw stdin lines without prompts, and enable the stdout hook.
- [x] 1.9 Document dependency/setup notes for `langchain-openai` (README or example doc).
- [x] 1.10 Add a root dependency manifest for runtime and test dependencies.

## 2. Validation
- [ ] 2.1 Manual smoke run of the stdin/stdout chat example (OpenAI key + simple prompt, then `/quit`).
- [ ] 2.2 Unit test: stdout hook renders expected text for representative plan/model/tool events.
