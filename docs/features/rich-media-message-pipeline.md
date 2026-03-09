---
change_ids: ["agentscope-d1-d3-message-pipeline", "transport-typed-payload-cutover", "message-input-boundary-cleanup"]
doc_kind: feature
topics: ["message-schema", "rich-media", "transport", "agent-input", "a2a"]
created: 2026-03-09
updated: 2026-03-09
status: active
mode: openspec
---

# Feature: rich-media-message-pipeline

## Scope

Land the rich-media message pipeline as a single governed delivery topic: canonical `Message`
schema cutover, typed transport payloads, public agent input normalization, and A2A/example
entrypoint migration to `text + attachments + data`.

This topic intentionally excludes the later runtime-lifecycle redesign for message delivery,
caching, compression, resume, and dispatch orchestration.

## OpenSpec Artifacts

- Proposal:
  - `openspec/changes/archive/2026-03-09-agentscope-d1-d3-message-pipeline/proposal.md`
  - `openspec/changes/archive/2026-03-09-transport-typed-payload-cutover/proposal.md`
  - `openspec/changes/archive/2026-03-09-message-input-boundary-cleanup/proposal.md`
- Design:
  - `openspec/changes/archive/2026-03-09-agentscope-d1-d3-message-pipeline/design.md`
  - `openspec/changes/archive/2026-03-09-transport-typed-payload-cutover/design.md`
  - `openspec/changes/archive/2026-03-09-message-input-boundary-cleanup/design.md`
- Specs:
  - `openspec/specs/rich-media-message-schema/spec.md`
  - `openspec/specs/transport-channel/spec.md`
  - `openspec/specs/interaction-dispatch/spec.md`
  - `openspec/specs/chat-runtime/spec.md`
  - `openspec/specs/typed-transport-replies/spec.md`
- Tasks:
  - `openspec/changes/archive/2026-03-09-agentscope-d1-d3-message-pipeline/tasks.md`
  - `openspec/changes/archive/2026-03-09-transport-typed-payload-cutover/tasks.md`
  - `openspec/changes/archive/2026-03-09-message-input-boundary-cleanup/tasks.md`

## Governance Anchors

- `docs/guides/Development_Constraints.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- `docs/design/Interfaces.md`
- `docs/design/modules/context/README.md`
- `docs/design/modules/transport/README.md`
- `docs/design/modules/model/README.md`
- `docs/design/modules/agent/README.md`

## Evidence

### Commands

- `openspec validate --spec-dir openspec/specs`
- `git diff --check`
- `./.venv/bin/pytest -q tests/integration/test_security_policy_gate_flow.py tests/unit/test_a2a.py tests/unit/test_transport_channel.py tests/unit/test_execution_control.py tests/unit/test_security_boundary.py tests/unit/test_governed_tool_gateway.py tests/unit/test_dare_agent_security_policy_gate.py tests/unit/test_dare_agent_security_boundary.py tests/unit/test_transport_adapters.py tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py tests/integration/test_p0_conformance_gate.py::test_step_driven_session_executes_validated_steps_in_order tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step tests/unit/test_dare_agent_step_driven_mode.py tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session tests/unit/test_event_sqlite_event_log.py tests/unit/test_builder_security_boundary.py::test_default_event_log_replay_returns_ordered_session_window`
- `GOVERNANCE_INTENT_GATE_CHANGED_FILES=$'client/main.py\ndare_framework/context/types.py\ndocs/features/rich-media-message-pipeline.md' GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE='zts212653/Deterministic-Agent-Runtime-Engine#206=merged' ./scripts/ci/check_governance_intent_gate.sh`

### Results

- `openspec validate --spec-dir openspec/specs`: baseline spec tree is valid before the
  implementation PR updates runtime code and evidence.
- `git diff --check`: message-schema and transport cutover branch stayed formatting-clean after
  rebasing onto the merged intent PR baseline.
- `./.venv/bin/pytest -q tests/integration/test_security_policy_gate_flow.py tests/unit/test_a2a.py tests/unit/test_transport_channel.py tests/unit/test_execution_control.py tests/unit/test_security_boundary.py tests/unit/test_governed_tool_gateway.py tests/unit/test_dare_agent_security_policy_gate.py tests/unit/test_dare_agent_security_boundary.py tests/unit/test_transport_adapters.py tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py tests/integration/test_p0_conformance_gate.py::test_step_driven_session_executes_validated_steps_in_order tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step tests/unit/test_dare_agent_step_driven_mode.py tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session tests/unit/test_event_sqlite_event_log.py tests/unit/test_builder_security_boundary.py::test_default_event_log_replay_returns_ordered_session_window`: passed (`142 passed, 1 warning`) after updating the remaining security-gate integration assertion to read canonical `Message.text` instead of the removed `Message.content`.
- `GOVERNANCE_INTENT_GATE_CHANGED_FILES=$'client/main.py\ndare_framework/context/types.py\ndocs/features/rich-media-message-pipeline.md' GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE='zts212653/Deterministic-Agent-Runtime-Engine#206=merged' ./scripts/ci/check_governance_intent_gate.sh`: passed, confirming the implementation PR now carries an active governed feature doc that references a merged intent PR.

### Behavior Verification

- Happy path: the implementation PR now lands canonical `Message(text + attachments + data)` flow
  through transport payloads, agent public inputs, A2A ingestion, and model adapter serialization,
  so a single user message can carry one text segment plus multiple image attachments.
- Error/fallback path: the last remaining legacy `Message.content` read in the security-gate flow
  is removed, so denied-tool regression coverage still records the structured `not_allow` tool
  result without breaking the `risk-matrix` and `p0-gate` CI bundles.

### Risks and Rollback

- Risk: the implementation PR still needs to append concrete runtime verification evidence and
  update the active feature record before merge.
- Rollback: if the topic scope changes materially, replace this intent record before merging the
  implementation PR instead of silently repurposing it.

### Review and Merge Gate Links

- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/206`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/204`
- Review request: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/206#issuecomment-4023104454`
- Implementation fix notes: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/204#issuecomment-4023016723`
