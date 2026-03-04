# P0 Gate Runbook

> Scope: `p0-conformance-gate` operational usage after the category matrix, CI entrypoint, and summary contract have been frozen.

## 1. Command of Record

Run the gate from the repository root:

```bash
.venv/bin/python scripts/ci/p0_gate.py
```

Expected success output:

```text
p0-gate: PASS
- SECURITY_REGRESSION: 0 failures
- STEP_EXEC_REGRESSION: 0 failures
- AUDIT_CHAIN_REGRESSION: 0 failures
```

The same command is used by `.github/workflows/ci-gate.yml` job `p0-gate`.

## 1.1 Ownership Mapping Health Check

Run ownership-map巡检 from repository root:

```bash
python scripts/ci/check_test_failure_ownership.py
```

Expected success output starts with:

```text
[failure-ownership] passed
```

This command is used by `.github/workflows/ci-gate.yml` job `failure-ownership-map` and enforces the
`失败测试 -> 责任模块 -> owner` mapping integrity for `p0-gate` categories.

## 2. Category Mapping

### SECURITY_REGRESSION

Primary signal:
- `tests/integration/test_security_policy_gate_flow.py`
- `tests/unit/test_dare_agent_security_policy_gate.py`
- `tests/unit/test_dare_agent_security_boundary.py`
- `tests/unit/test_transport_adapters.py`
- `tests/unit/test_examples_cli.py`
- `tests/unit/test_examples_cli_mcp.py`

Inspect first:
- `dare_framework/security/`
- `dare_framework/tool/_internal/governed_tool_gateway.py`
- `dare_framework/transport/_internal/adapters.py`
- `examples/05-dare-coding-agent-enhanced/cli.py`
- `examples/06-dare-coding-agent-mcp/cli.py`

### STEP_EXEC_REGRESSION

Primary signal:
- `tests/integration/test_p0_conformance_gate.py::test_step_driven_session_executes_validated_steps_in_order`
- `tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step`
- `tests/unit/test_dare_agent_step_driven_mode.py`

Inspect first:
- `dare_framework/agent/dare_agent.py`
- `dare_framework/agent/_internal/execute_engine.py`
- `dare_framework/plan/`

### AUDIT_CHAIN_REGRESSION

Primary signal:
- `tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session`
- `tests/unit/test_event_sqlite_event_log.py`
- `tests/unit/test_builder_security_boundary.py::test_default_event_log_replay_returns_ordered_session_window`

Inspect first:
- `dare_framework/event/_internal/sqlite_event_log.py`
- `dare_framework/event/kernel.py`
- `dare_framework/observability/_internal/event_trace_bridge.py`
- `dare_framework/agent/builder.py`

## 3. Local Troubleshooting Flow

1. Run `.venv/bin/python scripts/ci/p0_gate.py`.
2. Record the first failing summary block before any rerun.
3. Rerun only the category-local anchors listed in the summary.
4. Fix the regression, then rerun the full `p0-gate` command.
5. Do not claim the gate is fixed until the full command returns `PASS`.

If the summary itself looks malformed, rerun:

```bash
.venv/bin/python -m pytest -q tests/unit/test_p0_gate_ci.py
```

That suite locks the `PASS/FAIL + category + tests + modules + action` contract.

## 4. Release Archive Step

Every release candidate, release PR, or final tag cut that relies on protected-branch quality gates MUST archive the latest `p0-gate` result.

Minimum archive payload:
- exact command: `.venv/bin/python scripts/ci/p0_gate.py`
- exact summary text
- workflow/job URL when run in GitHub Actions
- release identifier (`tag`, `release PR`, or release issue)
- operator and timestamp

Archive location rule:
- preferred: release PR description or release issue checklist
- acceptable fallback: release note draft section named `P0 Gate`

If `p0-gate` is not green, the release must stop; do not archive a failed run as release evidence unless the release is explicitly aborted.

## 5. Flaky Handling Policy

P0 gate failures are blocker-grade until proven otherwise. Treat reruns as evidence collection, not as remediation.

Rules:
1. One immediate rerun is allowed only after preserving the first failing summary.
2. A category may be called flaky only if the same node id both fails and passes without code changes.
3. Flaky suspicion requires an issue or TODO entry that records:
   - failing node id
   - category label
   - first failed run link
   - rerun result
   - owner and expiry
4. A flaky anchor must not be silently removed from `scripts/ci/p0_gate.py`.
5. Any temporary downgrade or quarantine requires a docs-first change that names the replacement anchor or the rollback plan.

Escalation threshold:
- two flaky incidents for the same node id within seven days triggers quarantine review
- quarantine review must finish within two business days

## 6. Branch Protection Follow-up

After `p0-conformance-gate` merges, a repository administrator still needs to add `p0-gate` to the protected branch required checks / ruleset. That step is outside the repository contents and is tracked separately in `docs/governance/branch-protection.md`.
