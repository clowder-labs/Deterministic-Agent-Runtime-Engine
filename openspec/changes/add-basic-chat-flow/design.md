## Context
The current runtime loop does not yet invoke the model adapter, and prompts are not wired into context assembly. We need a minimal, LLM-driven execution path that aligns with the architecture doc (LLM-driven Execute Loop) and enables an interactive stdio chat client with readable tracing.

## Goals / Non-Goals
- Goals:
  - Provide a base English system prompt via the default `IPromptStore` implementation.
  - Implement an OpenAI model adapter using `langchain-openai` that conforms to `IModelAdapter`.
  - Add a local command tool with workspace root restrictions for write operations.
  - Enable an interactive stdin/stdout chat client that loops until `/quit`, preserves session context across turns, and returns model responses.
  - Dispatch runtime events to hooks and expose plan/model/tool details for tracing.
  - Provide a stdout hook that prints human-readable summaries of those events.
  - Expose `workspace_roots` in config/session so tools can enforce scope.
- Non-Goals:
  - Full planner/reflection improvements or complex tool selection heuristics.
  - Complete plugin discovery/registration for all component types.
  - Extensive safety approvals (policy engine remains AllowAll for now).
  - Context truncation, summarization, or token budgeting for multi-turn sessions.

## Decisions
- Use a minimal LLM-driven execute loop inside `AgentRuntime` that:
  - Builds messages from the base system prompt + user input (via a prompt-aware context assembler).
  - Calls `IModelAdapter.generate(...)` with tool definitions from `ToolRuntime`.
  - Executes tool calls returned by the model and appends results back into the message history.
  - Terminates when the model returns a response without tool calls, capturing the text as output.
- Dispatch hook events inside `AgentRuntime._log_event` after the event log append, treating hook failures as best-effort and non-fatal.
- Emit explicit events for plan proposals, model responses, and tool results with concise payloads suitable for hook rendering.
- Record hook failures as runtime events (for example `hook.error`); MVP logging may surface via stdout.
- Store the base system prompt in the default `InMemoryPromptStore` with a stable name (e.g., `base.system`).
- Add `Config.workspace_roots: list[str]` and propagate it into the run context (e.g., via `SessionContext` attached to `RunContext`) for tool enforcement.
- Implement `RunCommandTool` as a first-party tool with `NON_IDEMPOTENT_EFFECT` risk level and a working directory restricted to `workspace_roots`.
- Provide an interactive stdin/stdout chat example (not a full CLI framework) that maintains an in-memory conversation history across turns and reads raw stdin lines without extra prompts.
- The stdout hook prints line-oriented tagged messages and flushes output for interactive usage.

## Alternatives Considered
- Implement a dedicated `ChatRuntime` separate from `AgentRuntime`.
  - Rejected for now to keep a single primary runtime path.
- Treat the model as a tool and keep the existing execute loop unchanged.
  - Rejected because it hides the LLM execution path and complicates tool call handling.

## Risks / Trade-offs
- Minimal loop may not cover all edge cases (multi-turn state, advanced tool selection).
  - Acceptable for the first milestone; future iterations can expand.
- Adding a new dependency (`langchain-openai`) without a package manager may require manual setup.
- Hook output volume may be high; keep messages concise and plan for filtering later.

## Migration Plan
- No migration needed (early-stage framework). Introduce new components and wire them into the builder/runtime path.

## Open Questions
- None. Requirements specified by the user are treated as the current baseline.
