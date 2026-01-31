# Module: hook

> Status: interface + helper only (2026-01-31). TODO indicates missing integration.

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

- **Agent**：应在运行时触发 hook（TODO）。
- **Config/Managers**：可加载多 hook 实现并按顺序执行。

## 5. 现状与限制

- DareAgent 接收 hooks 但未实际调用（TODO）。
- Hook payload schema 未统一定义。

## 6. TODO / 未决问题

- TODO: 在 DareAgent 生命周期注入 hook 调用点。
- TODO: 明确 hook 的 payload schema 与错误处理策略。
