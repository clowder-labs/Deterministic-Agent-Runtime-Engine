## 1. Internal module scaffolding

- [x] 1.1 Create `_internal` orchestration modules for session, milestone, execute, and tool responsibilities under `dare_framework/agent/_internal/`.
- [x] 1.2 Define minimal internal call contracts so extracted modules can receive runtime dependencies explicitly (context, security, logging, hooks, approvals).
- [x] 1.3 Add module-level docstrings/comments clarifying responsibility boundaries.

## 2. Runtime extraction with behavior parity

- [x] 2.1 Extract tool-loop execution logic from `DareAgent` into a dedicated internal tool executor while preserving security/approval/hook/event semantics.
- [x] 2.2 Extract execute-loop branching (model-driven / step-driven) into an internal execute engine while keeping existing output/error behavior.
- [x] 2.3 Extract milestone-loop orchestration into an internal milestone orchestrator, preserving remediation/policy failure flows.
- [x] 2.4 Keep `DareAgent` as the public API entry point and reduce it to orchestration wiring + top-level state transitions.

## 3. Verification and regression protection

- [ ] 3.1 Add/adjust targeted unit tests for extracted execution units (success/failure/approval/policy/retry branches).
- [x] 3.2 Run affected unit test suites for agent execute/tool/milestone paths and fix regressions.
- [x] 3.3 Run design-doc drift and compile checks to ensure governance and structural integrity remain green.

## 4. Documentation and closeout

- [x] 4.1 Update `docs/design/modules/agent/TODO.md` to reflect A-101 status/evidence.
- [x] 4.2 Update `docs/design/TODO_INDEX.md` to keep global TODO index aligned with A-101 progress.
- [x] 4.3 Mark OpenSpec tasks complete with evidence references once implementation and verification pass.

## Evidence

- Runtime extraction:
  - `dare_framework/agent/dare_agent.py`
  - `dare_framework/agent/_internal/session_orchestrator.py`
  - `dare_framework/agent/_internal/milestone_orchestrator.py`
  - `dare_framework/agent/_internal/execute_engine.py`
  - `dare_framework/agent/_internal/tool_executor.py`
  - `dare_framework/agent/_internal/orchestration.py`
- New targeted tests:
  - `tests/unit/test_dare_agent_orchestration_split.py`
  - Current scope verifies facade-to-internal delegation wiring; branch-level success/failure/approval/policy/retry coverage remains pending under task 3.1.
- Regression suites executed:
  - `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_five_layer_agent.py tests/unit/test_dare_agent_hook_governance.py tests/unit/test_dare_agent_hook_transport_boundary.py tests/unit/test_dare_agent_orchestration_split.py`
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m compileall -q dare_framework tests`
- Governance note:
  - `./scripts/ci/check_design_doc_drift.sh` is not present in this branch; no local executable drift script found under `scripts/ci` or workflow definitions.
