## 1. Spec and contract scaffolding

- [x] 1.1 Add/adjust unit tests that fail when SimpleChatAgent does not return envelope-shaped `RunResult.output`.
- [x] 1.2 Add/adjust unit tests that fail when ReactAgent does not return envelope-shaped `RunResult.output`.
- [x] 1.3 Add/adjust unit tests that fail when DareAgent does not return envelope-shaped `RunResult.output`.

## 2. Runtime implementation

- [x] 2.1 Add a reusable output-envelope helper that converts heterogeneous outputs into `{content, metadata, usage}`.
- [x] 2.2 Update `SimpleChatAgent.execute(...)` to return the standardized output envelope.
- [x] 2.3 Update `ReactAgent.execute(...)` to return the standardized output envelope.
- [x] 2.4 Update `DareAgent.execute(...)` to return the standardized output envelope while preserving existing lifecycle/hook behavior.

## 3. Verification and governance

- [x] 3.1 Run targeted unit tests for simple/react/dare agent output contracts and fix regressions.
- [x] 3.2 Run compile checks to ensure no syntax/runtime contract regressions.
- [x] 3.3 Update `docs/design/modules/agent/TODO.md` and `docs/design/TODO_INDEX.md` to reflect A-103 progress/evidence.
- [x] 3.4 Mark this tasks file complete with executed command evidence once checks pass.

## Evidence

- Runtime changes:
  - `dare_framework/agent/_internal/output_normalizer.py`
  - `dare_framework/agent/simple_chat.py`
  - `dare_framework/agent/react_agent.py`
  - `dare_framework/agent/dare_agent.py`
- Tests:
  - `tests/unit/test_agent_output_envelope.py`
  - `tests/unit/test_five_layer_agent.py`
  - `tests/unit/test_builder_tool_gateway.py`
- Commands:
  - `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_agent_output_envelope.py`
  - `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_agent_output_envelope.py tests/unit/test_five_layer_agent.py tests/unit/test_builder_tool_gateway.py tests/unit/test_react_agent_gateway_injection.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py tests/unit/test_client_cli.py tests/unit/test_a2a.py`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m compileall -q dare_framework tests`
