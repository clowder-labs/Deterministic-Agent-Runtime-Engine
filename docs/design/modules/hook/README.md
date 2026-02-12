# Module: hook

> Status: governance v1 integrated with DareAgent (2026-02-12).

## 1. 定位与职责

- 提供生命周期 hook 扩展点（观测/插桩/策略）。
- 提供治理决策能力：`allow/block/ask`。
- 支持受控 patch（白名单字段）与 shadow rollout。

## 2. 关键概念与数据结构

- `HookPhase`：生命周期阶段枚举（BEFORE_RUN/AFTER_RUN/BEFORE_TOOL/...）。
- `HookDecision`：治理决策（allow/block/ask）。
- `HookEnvelope`：typed hook 请求封装（version/phase/context/payload）。
- `HookResult`：统一返回结构（decision/patch/message）。
- `IHook`：Hook 实现接口。
- `IExtensionPoint`：注册与触发 hook 的扩展点。

## 3. 关键接口与实现

- Kernel：`IHook`, `IExtensionPoint`（`dare_framework/hook/kernel.py`）
- Manager：`IHookManager`（`dare_framework/hook/interfaces.py`）
- Runtime：
  - `HookExtensionPoint`（选择/执行/仲裁/patch 校验）
  - `LegacyHookAdapter`（旧 hook 兼容）
- Helper：`CompositeExtensionPoint`（`dare_framework/hook/_internal/composite_extension_point.py`）

## 4. 与其他模块的交互

- **Agent**：DareAgent 在 `before_model`、`before_tool`、`before_context_assemble`、`before_verify` 消费治理决策。
- **Config/Managers**：支持 hooks 配置（version/defaults/entries）及 system/config/code 的稳定排序。
- **Observability**：输出 hook 治理相关指标（包含 `hook.overhead_ratio`）。

## 5. 现状与限制

- 目前治理执行优先接入 DareAgent，其他 agent 仍可按需迁移。
- phase schema 与 patch allowlist 已建立，但业务字段仍可继续细化。

## 6. TODO / 未决问题

- TODO: 扩展 ask 决策的人机审批桥接（当前无审批桥时为拒绝执行）。
- TODO: 按 phase 完善 patch allowlist 与策略审计字段。

## 7. Design Clarifications (2026-02-03)

- V1 明确最小契约：`HookEnvelope/HookResult` + phase schema。
- 迁移策略：legacy hook 可通过 adapter 进入 v1 dispatch；shadow 模式下只记录不拦截。
