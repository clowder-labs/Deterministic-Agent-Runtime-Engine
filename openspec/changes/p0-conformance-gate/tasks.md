## 1. Define Gate Scope

- [x] 1.1 定义 `p0-gate` 覆盖的三类不变量与验收阈值。  
  Evidence: `openspec/changes/p0-conformance-gate/design.md` 已固化 `SECURITY_REGRESSION` / `STEP_EXEC_REGRESSION` / `AUDIT_CHAIN_REGRESSION` 三类 category matrix，并为 required-mode promotion 定义 “单次运行全绿” 阈值。  
  Last Updated: `2026-03-04`
- [x] 1.2 明确每类不变量对应的测试文件与责任模块。  
  Evidence: `openspec/changes/p0-conformance-gate/design.md` 的 Gate Scope Matrix 已列出现有 anchor suites、后续必须补的 integration anchors，以及各 category 的 primary ownership modules。  
  Last Updated: `2026-03-03`
- [x] 1.3 定义标准失败标签与 CI summary 输出格式。  
  Evidence: `openspec/changes/p0-conformance-gate/specs/p0-conformance-gate/spec.md` 与 `openspec/changes/p0-conformance-gate/design.md` 已同步固定 failure labels 与 summary contract；`docs/governance/branch-protection.md` 已把 `p0-gate` rollout 前提写成未来 required-check 条件。  
  Commands: `openspec validate p0-conformance-gate --type change --strict --json --no-interactive` => `1/1` valid；`./scripts/ci/check_governance_evidence_truth.sh` => `passed`  
  Last Updated: `2026-03-03`

## 2. Build P0 Test Suite

- [x] 2.1 新增集成测试覆盖安全门控主链路（allow/deny/approve_required）。  
  Evidence: `tests/integration/test_security_policy_gate_flow.py` 现在显式覆盖 read-only `allow`、`deny_capability_ids` 触发的 `not_allow`、以及 high-risk `approve_required -> grant` 主链路。  
  Commands: `../../.venv/bin/python -m pytest -q tests/integration/test_security_policy_gate_flow.py` => `3 passed, 1 warning`；`../../.venv/bin/python -m pytest -q tests/unit/test_dare_agent_security_policy_gate.py tests/unit/test_dare_agent_security_boundary.py tests/unit/test_five_layer_agent.py` => `50 passed, 1 warning`  
  Last Updated: `2026-03-03`
- [x] 2.2 新增集成测试覆盖 `step_driven` 执行闭环。  
  Evidence: `tests/integration/test_p0_conformance_gate.py` 现在通过完整 `agent("task")` 会话覆盖 `step_driven` 的闭环集成路径：`planner.decompose -> planner.plan -> validator.validate_plan -> execute -> validator.verify_milestone`，并显式验证 happy path 的顺序执行 / `_previous_output` 传递，以及 fail-fast path 在首个失败 step 后不会继续执行后续 step。  
  Commands: `../../.venv/bin/python -m pytest -q tests/integration/test_p0_conformance_gate.py` => `2 passed, 1 warning`  
  Last Updated: `2026-03-03`
- [x] 2.3 新增集成测试覆盖默认 event log hash-chain/replay。  
  Evidence: `tests/integration/test_p0_conformance_gate.py` 现在补齐默认 SQLite event log 的 runtime integration anchor：真实会话落盘后验证 `replay(from_event_id=session.start)` 返回同一 session window，并且 `verify_chain()` 在正常数据上通过、在篡改落盘 payload 后失败。  
  Commands: `../../.venv/bin/python -m pytest -q tests/integration/test_p0_conformance_gate.py` => `3 passed, 1 warning`  
  Last Updated: `2026-03-03`
- [x] 2.4 增加关键单测确保契约字段与错误码稳定。  
  Evidence: `dare_framework/transport/_internal/adapters.py`，`tests/unit/test_transport_adapters.py`（新增 slash 命令到 `resource:action` 的标准化与审批参数提取断言）；`examples/05-dare-coding-agent-enhanced/cli.py`、`examples/06-dare-coding-agent-mcp/cli.py`（审批 action 调用统一为 `invoke(action, **params)`）  
  Commands: `.venv/bin/pytest -q tests/unit/test_transport_adapters.py::test_stdio_slash_command_maps_to_resource_action_id tests/unit/test_transport_adapters.py::test_stdio_slash_command_extracts_approval_action_params` => `2 passed`；`.venv/bin/pytest -q tests/unit/test_transport_adapters.py tests/unit/test_interaction_dispatcher.py tests/unit/test_transport_channel.py tests/integration/test_client_cli_flow.py` => `33 passed, 1 warning`；`.venv/bin/pytest -q tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py` => `22 passed, 1 warning`  
  Last Updated: `2026-03-01`

## 3. CI Integration

- [x] 3.1 在 CI workflow 增加 `p0-gate` job 与命令入口。  
  Evidence: `.github/workflows/ci-gate.yml` 已新增 `p0-gate` job，并统一调用 `python scripts/ci/p0_gate.py` 作为 CI 入口；`scripts/ci/p0_gate.py` 固化了三类 category 的 gate bundle。  
  Commands: `../../.venv/bin/python scripts/ci/p0_gate.py` => `p0-gate: PASS`  
  Last Updated: `2026-03-03`
- [ ] 3.2 将 `p0-gate` 配置为主分支 required check。  
  Note: 该项需要 GitHub branch protection / ruleset 管理员权限；当前仓库内已完成 job 名称与 rollout 文档对齐，但尚未执行远端仓库设置。执行清单见 `docs/governance/branch-protection.md` 的 `P0-Gate Required Check Rollout (Admin Checklist)` 章节，关闭时需补 settings + blocked/pass run 证据链接。
- [x] 3.3 输出标准化门禁报告（通过率、失败类型、建议排查点）。  
  Evidence: `scripts/ci/p0_gate.py` 的 `format_summary()` 已固定 `PASS/FAIL + category label + failing tests + modules + owner + action` 文本格式，并写入 `GITHUB_STEP_SUMMARY`；`scripts/ci/check_test_failure_ownership.py` + `.github/workflows/ci-gate.yml` `failure-ownership-map` job 形成例行映射巡检；`tests/unit/test_p0_gate_ci.py` 锁定 summary contract。  
  Commands: `../../.venv/bin/python -m pytest -q tests/unit/test_p0_gate_ci.py` => `4 passed`；`python scripts/ci/check_test_failure_ownership.py` => `[failure-ownership] passed`；`../../.venv/bin/python scripts/ci/p0_gate.py` => `p0-gate: PASS`  
  Last Updated: `2026-03-03`

## 4. Operationalization

- [x] 4.1 更新开发文档，说明本地运行与故障排查流程。  
  Evidence: `docs/guides/P0_Gate_Runbook.md` 已定义 command-of-record、本地分诊顺序、按 category 的定位入口；`docs/guides/Team_Agent_Collab_Playbook.md` 与 `docs/README.md` 已补入口链接。  
  Commands: `../../.venv/bin/python scripts/ci/p0_gate.py` => `p0-gate: PASS`；`./scripts/ci/check_governance_evidence_truth.sh` => `passed`  
  Last Updated: `2026-03-03`
- [x] 4.2 在发布流程增加 `p0-gate` 结果归档步骤。  
  Evidence: `docs/guides/P0_Gate_Runbook.md` 已固定 release archive 的最小字段、归档位置规则与“失败即停止发布”要求。  
  Commands: `./scripts/ci/check_governance_evidence_truth.sh` => `passed`  
  Last Updated: `2026-03-03`
- [x] 4.3 制定 flaky 用例处理规则与时限。  
  Evidence: `docs/guides/P0_Gate_Runbook.md` 已定义 flaky 认定条件、一次性 rerun 上限、issue/TODO 记录字段、7 天/2 个 incident 触发的 quarantine review、以及 2 个工作日内的处理时限。  
  Commands: `./scripts/ci/check_governance_evidence_truth.sh` => `passed`  
  Last Updated: `2026-03-03`

## 5. Baseline Recovery Evidence

- [x] 5.1 修复审批异常语义回归，恢复安全门控关键失败分支的结构化错误前缀契约。
  Evidence: `dare_framework/tool/_internal/governed_tool_gateway.py`
  Commands: `.venv/bin/pytest -q tests/unit/test_dare_agent_security_boundary.py::test_tool_loop_approval_evaluate_exception_returns_structured_failure tests/unit/test_dare_agent_security_boundary.py::test_tool_loop_approval_wait_exception_returns_structured_failure` => `2 passed`；`.venv/bin/pytest -q` => `504 passed, 12 skipped, 1 warning`
  Last Updated: `2026-03-01`
