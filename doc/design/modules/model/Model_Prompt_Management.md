# DARE Framework 模型与 Prompt 管理设计（Draft）

> 状态：草案（用于评审）
>
> 本文描述 DARE Framework 在 `model` 域内如何管理与解析 Prompt，并定义模型调用输入 `ModelInput`，给出数据结构、解析顺序、扩展点与集成方式。
>
> 相关规范：`openspec/changes/add-prompt-management/`

---

## 1. 目标与边界

### 目标
- 为框架提供统一、可扩展的 Prompt 管理与解析机制。
- 允许按模型身份（`IModelAdapter.name`）选择最优 Prompt。
- 支持 builder 与 config 的显式覆盖，保持确定性与可审计性。
- 明确扩展点，方便后续接入远端 Prompt 源或新 Prompt role。

### 非目标
- 不引入 Prompt DSL/模板引擎。
- 不引入动态运行时 Prompt 变更（热更新）。
- 不在本阶段定义多阶段 prompt pack（plan/execute/verify）。

---

## 2. 术语与命名

- **Prompt**：存储层/配置层的提示词定义（带 `prompt_id`、`supported_models`、`order` 等元信息），与运行时 `ModelInput` 区分。
- **ModelInput**：模型调用的运行时请求结构（`messages + tools + metadata`），替代旧的 `Prompt` 命名。
- **sys_prompt**：Context 中保存的结构化系统提示定义（`Prompt`），不是字符串。

---

## 3. 领域归属（Model DDD）

Prompt 与模型适配器的组合能力属于 `model` 域：

```
dare_framework/model/
  types.py          # Prompt / ModelInput（运行时输入）/ ModelResponse / GenerateOptions
  kernel.py         # IModelAdapter
  interfaces.py     # IModelAdapterManager / IPromptLoader / IPromptStore
  _internal/        # 默认实现（模型适配器 + Prompt loaders + Layered store）
```

- `IModelAdapter` 只负责模型调用与暴露稳定身份（`name`）。
- Prompt 解析与选择由 model 域内的 Prompt store 实现负责。
- Context assembly 仅消费已解析的系统提示定义，不包含解析逻辑。

---

## 4. 核心概念

### 4.1 Prompt（定义层）
从 manifest 中读取的静态定义，字段如下：
- `prompt_id` (string)
- `role` (string, aligns with `Message.role`)
- `content` (string)
- `supported_models` (list[string], may include `*`)
- `order` (int, higher is preferred)
- `version` (string, optional)
- `name` (string, optional)
- `metadata` (object, optional)

语义约束：
- `supported_models` 必须至少包含一个值；`*` 表示任意模型。
- `order` 是确定性优先级，数值越大越优先。
- `prompt_id` 是稳定标识，用于 override 与配置引用。

### 4.2 ModelInput（运行时输入）
`ModelInput` 是模型调用的运行时结构（`messages + tools + metadata`），来自：
1) 已解析的系统提示定义 → 转为 `Message`
2) Context assembled messages（STM/LTM/knowledge）
3) Tool listing（可信来源）

### 4.3 Context 内的系统提示
Context 保留结构化的系统提示定义（而非字符串）：
- `sys_prompt: Prompt | None`

`Context.assemble()` 返回的 `AssembledContext` 暴露该字段，agent 在构建 `ModelInput` 时将
`sys_prompt` 转换为 `Message` 并置于消息首位。

---

## 5. Prompt Manifest 与加载

### 5.1 文件结构
manifest 以 JSON 存储：

```json
{
  "prompts": [
    {
      "prompt_id": "base.system",
      "role": "system",
      "content": "You are a deterministic agent runtime...",
      "supported_models": ["*"],
      "order": 0
    }
  ]
}
```

### 5.2 路径规则
通过 config 指定 `prompt_store_path_pattern`，默认 `.dare/_prompts.json`。
默认加载顺序：
1) workspace 目录
2) user 目录
3) built-in

### 5.3 基础校验（最小规则）
Loader 至少保证：
- `prompts` 为数组
- 每个元素包含 `prompt_id` / `role` / `content` / `supported_models` / `order`
- `order` 为整数

其他字段保留原样（用于扩展）。

---

## 6. 解析与选择流程

### 6.1 选择优先级（builder / config / store）
1) builder 显式 prompt override  
2) builder 显式 `prompt_id` override  
3) config `default_prompt_id`  
4) 基于 model identity 的 prompt store 解析

如果 builder 同时设置 prompt 与 `prompt_id`，最后一次调用覆盖前一次，确保只有一个 override 生效。

### 6.2 Store 解析规则
当调用 `IPromptStore.get(prompt_id, model, version)`：
- 过滤 `prompt_id` 与 `version`（若提供版本）
- 匹配 `supported_models` 包含 model 或 `*`
- 选择最高 `order`
- tie-break：workspace > user > built‑in → manifest 稳定顺序

---

## 7. 组件接口

### 7.1 IPromptLoader（公开接口）
负责从单一来源加载 Prompt 列表：
- 必须保持稳定顺序
- 可实现：FileSystemPromptLoader、BuiltInPromptLoader、RemotePromptLoader（future）

### 7.2 IPromptStore（公开接口）
负责提供解析后的 Prompt：
- 支持 model-aware 选择
- 负责 precedence 与 deterministic tie-break

---

## 8. 集成路径

### 8.1 Builder 集成
Builder 提供：
- prompt override（直接覆盖）
- prompt_id override（通过 store 解析）
- config 可提供 `default_prompt_id`

Builder 内部使用单一 override 槽位（`prompt_id` 或 `prompt` 二选一）。

### 8.2 Context Assembly
组装 context 时：
- 将解析出的 base system prompt 作为第一条消息
- 再拼接 STM/LTM 消息与工具清单

---

## 9. 确定性与错误处理

- 所有 loader 必须保持稳定顺序，以确保同 `order` 下的 tie-break 可复现。
- 若 `prompt_id` 不存在或无匹配模型，`IPromptStore.get(...)` 返回 not-found。
- 内置 `base.system` 的 `supported_models: ["*"]` 与最低 `order` 保证默认可用。

---

## 10. 扩展点

- 新 Prompt role（例如 planner/validator system）
- 新 prompt source（RemotePromptLoader）
- 多配置策略（按 workspace/tenant 启用不同 manifest）

---

## 11. 最小内置基线

内置 `base.system` Prompt：
- `supported_models: ["*"]`
- `order: 0`（最低优先级）

确保无外部覆盖时仍可正常工作。

---

## 12. 实现落点（代码结构建议）

```
dare_framework/model/
  types.py          # Prompt / ModelInput / ModelResponse / GenerateOptions
  kernel.py         # IModelAdapter
  interfaces.py     # IModelAdapterManager / IPromptLoader / IPromptStore
  _internal/
    filesystem_prompt_loader.py
    builtin_prompt_loader.py
    layered_prompt_store.py
```

Context 与 builder 的集成点：
- `dare_framework/context/types.py`：`AssembledContext.sys_prompt`
- `dare_framework/context/_internal/context.py`：保存并暴露 `sys_prompt`
- `dare_framework/builder/builder.py`：override 解析 + store 选择
- `dare_framework/agent/_internal/*`：`ModelInput` 组装（sys_prompt → Message）
