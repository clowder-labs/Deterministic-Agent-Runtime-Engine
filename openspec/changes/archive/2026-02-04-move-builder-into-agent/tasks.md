## 1. Agent Domain Restructure
- [x] 1.1 Move `BaseAgent` to a public agent module (e.g., `dare_framework/agent/base_agent.py`) and update imports.
- [x] 1.2 Relocate builder implementation into the agent domain (e.g., `dare_framework/agent/builder.py`) while preserving logic.
- [x] 1.3 Remove the `dare_framework/builder` package from the canonical surface.

## 2. API Surface Updates
- [x] 2.1 Add `BaseAgent.simple_chat_agent_builder(...)` and `BaseAgent.five_layer_agent_builder(...)` factory methods.
- [x] 2.2 Update `dare_framework/agent/__init__.py` exports to include builders and `BaseAgent`.

## 3. Examples, Tests, Docs
- [x] 3.1 Update examples to use `BaseAgent` builder factories (basic-chat, tool-management, base_tool).
- [x] 3.2 Update unit tests that import the builder facade to the new API.
- [x] 3.3 Update documentation references that mention `Builder` or `dare_framework.builder`.

## 4. Validation
- [x] 4.1 Run targeted unit tests for builder behavior.
- [x] 4.2 Validate example entrypoints still run with the new API.
