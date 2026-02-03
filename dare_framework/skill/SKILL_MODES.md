# Skill 模式设计

支持两种 skill 加载与挂载方式：**persistent_skill_mode**（单 skill 常驻）与 **auto_skill_mode**（多 skill 目录 + 按需加载完整内容）。

---

## 目标

| 模式 | 行为 |
|------|------|
| **persistent_skill_mode** | 启动时从**一个**路径（`initial_skill_path`）加载**一个** skill，在 **agent 初始化（build）时** 就把该 skill 的**完整内容**合并进 sys_prompt 并写入 context；assemble 时不再对这份 skill 做合并。 |
| **auto_skill_mode** | 见下节「auto_skill_mode 流程」。 |

---

## auto_skill_mode 流程

1. **带精简描述的 context 作为 LLM 输入，做 function call**
   - Build 时只把**精简描述（skill 目录）**合并进 sys_prompt，写入 context。
   - 第一次（或当前轮）调用 LLM 时，输入 = 该 context（仅含 base + 精简目录），LLM 据此做 **function call**。

2. **LLM 返回要执行 search_skill 加载某 skill（如 skill A）**
   - LLM 决定使用某个 skill 时，返回对 **search_skill(skill_id="A")** 的调用。

3. **Tool execution：执行 search_skill，把 A 的完整内容放到某个 dict**
   - 执行 **search_skill(skill_id="A")**（视为 **tool execution**）。
   - 从 SkillStore 取出 skill A 的**完整内容**，写入**一个 dict**（例如「已加载完整内容的 skill 集合」）。该 dict 仅在此阶段被更新，不在此刻改 sys_prompt。

4. **Assemble：把 dict 里的信息加到 context，作为下次 LLM 的输入**
   - **Assemble** 时，从上述 dict 中取出已加载的完整 skill 内容，**合并进 context**（例如合并进当次的 sys_prompt）。
   - 组装后的 context = base + 精简目录 + dict 中的完整 skill 内容，作为**下一次**调用 LLM 的输入。

小结：**精简 context → LLM function call → search_skill tool execution（完整内容入 dict）→ assemble（dict → context）→ 下次 LLM 输入**。

---

## 分层（从上到下）

### 1. 配置（Config）

- **skill_mode**：`"persistent_skill_mode"` \| `"auto_skill_mode"`
- **initial_skill_path**：单路径，persistent 用
- **skill_paths**：多路径列表，auto 用

### 2. 技能内容（Skill + prompt_enricher）

- **精简**：用 `Skill.id` / `name` / `description` 拼成「可选 skill 目录」→ `enrich_prompt_with_skill_summaries(base_prompt, skills)`
- **完整**：单 skill 的 content + scripts → `enrich_prompt_with_skill(base_prompt, skill)`

### 3. 上下文与「已加载完整内容的 dict」

- **persistent**：不在 assemble 里合并；build 时 builder 已将「base + 单 skill 完整内容」写入 `context._sys_prompt`，assemble 直接用这份 `_sys_prompt`。
- **auto**：
  - 维护一个 **dict**（或等价结构），用于存放 **search_skill tool execution** 拉取的 skill 完整内容。
  - **Tool execution**：search_skill(skill_id) 执行时，把对应 skill 的完整内容写入该 dict。
  - **Assemble**：从该 dict 取出内容，合并进 context（如合并进 sys_prompt），得到**下次 LLM 的输入**。

### 4. 工具（search_skill）

- 仅 **auto_skill_mode** 需要。
- **search_skill(skill_id)**：从 SkillStore 按 id 取 Skill；若存在则把该 skill 的**完整内容**写入上述 dict（tool execution 的职责）；若不存在则返回失败并可列出可用 skill_id。

### 5. 组装（Builder）

- 读取 `skill_mode`。
- **persistent_skill_mode**：
  - 只处理 `initial_skill_path`：单路径加载 → `set_skill` → 在 **build 时** 用 `enrich_prompt_with_skill(sys_prompt, context.current_skill())` 得到「base + 单 skill 完整」→ 赋给 `context._sys_prompt`。
  - 不注册 search_skill / run_skill_script（除非后续单独要求）。
- **auto_skill_mode**：
  - 从 `skill_paths` 加载全部 skills，建 SkillStore。
  - build 时用 `enrich_prompt_with_skill_summaries(base_sys_prompt, skills)` 得到「base + 精简目录」→ 赋给 `context._sys_prompt`。
  - 注册 **search_skill** 和 **run_skill_script**，并注入 SkillStore 与可写入的 dict（或 context 上暴露的写入接口）。

---

## 数据流小结

| 模式 | Build 时 | Tool execution | Assemble 时 |
|------|----------|----------------|-------------|
| **persistent** | base + 单 skill 完整 → `context._sys_prompt` | 无 | 直接用 `_sys_prompt`。 |
| **auto** | base + 精简目录 → `context._sys_prompt`；注册 search_skill。 | LLM 返回 search_skill(A) → 执行 search_skill，把 A 的完整内容写入 **dict**。 | 从 **dict** 取出已加载内容，合并进 context，作为**下次** LLM 输入。 |

---

## 配置示例

**persistent_skill_mode（单 skill 常驻）：**

```json
{
  "skill_mode": "persistent_skill_mode",
  "initial_skill_path": ".dare/skills/pdf"
}
```

**auto_skill_mode（多 skill 目录 + 按需加载）：**

```json
{
  "skill_mode": "auto_skill_mode",
  "skill_paths": [".dare/skills/pdf", ".dare/skills/code-review"]
}
```
