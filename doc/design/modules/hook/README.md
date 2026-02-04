# Module: hook

> Status: integrated with DareAgent (2026-02-04). TODO indicates remaining gaps.

## 1. 定位与职责

- 提供生命周期 hook 扩展点（观测/插桩/策略）。
- 默认 best-effort：hook 失败不影响主流程。

## 2. 关键概念与数据结构

- `HookPhase`：生命周期阶段枚举（BEFORE_RUN/AFTER_RUN/BEFORE_TOOL/...）。
- `IHook`：Hook 实现接口。
- `IExtensionPoint`：注册与触发 hook 的扩展点。

## 3. 关键接口与实现

- Kernel：`IHook`, `IExtensionPoint`（`dare_framework/hook/kernel.py`）
- Manager：`IHookManager`（`dare_framework/hook/interfaces.py`）
- Helper：`CompositeExtensionPoint`（`dare_framework/hook/_internal/composite_extension_point.py`）

## 4. 与其他模块的交互

- **Agent**：DareAgent 已在生命周期阶段触发 hook。
- **Config/Managers**：可加载多 hook 实现并按顺序执行。

## 5. 现状与限制

- DareAgent 会触发 HookPhase 生命周期事件；其他 agent 仍未接入。
- Hook payload schema 未统一定义。

## 6. TODO / 未决问题

- TODO: 明确 hook 的 payload schema 与错误处理策略。

## 7. Design Clarifications (2026-02-03)

- Doc gap: hook payload schema needs a minimal contract (observability relies on it).
- Impl gap: DareAgent now emits hooks; update module doc to reflect actual integration.
