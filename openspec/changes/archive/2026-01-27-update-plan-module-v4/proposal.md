# 变更：对齐 V4 设计的 plan 模块

## 为什么
当前 `dare_framework/plan` 已有类型与接口，但缺少一份明确的 V4 设计对齐规范（尤其是“Proposed vs Validated”、“可信元数据派生”、“Plan Attempt Isolation”等核心约束的落地说明）。为了确保规划闭环在可信边界、审计与可扩展性上与 V4 设计一致，需要为 plan 模块补齐规格与设计文档，并明确后续实现的范围与边界。

## 变更内容
- 为 plan 模块新增一份 V4 对齐的规格说明（plan-module spec）。
- 明确 plan 领域的数据模型边界：Proposed/Validated 分层、Envelope/ToolLoopRequest 的职责、验证与补救的返回语义。
- 记录与 V4 五层循环一致的计划尝试隔离要求及其在 plan 模块中的数据承载方式。
- 在设计文档中说明与 tool registry / security boundary / event log 的交互边界与可信派生规则。
 - 变更范围仅覆盖 `dare_framework`，不涉及 `dare_framework3_4`。

## 影响
- 影响规格：新增 `plan-module` 规格（与 `core-runtime`、`interface-layer`、`define-core-models` 交叉引用）。
- 影响代码（实现阶段）：`dare_framework/plan/*`、`dare_framework/agent/_internal/five_layer.py`、可能涉及 `dare_framework/security/*` 与 `dare_framework/tool/*` 的对齐点。
