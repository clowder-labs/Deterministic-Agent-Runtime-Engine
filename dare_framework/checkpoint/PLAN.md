# Checkpoint 现场保存与恢复 — 完整计划

本文档记录 DARE 框架内 Checkpoint 能力的完整设计：支持现场保存、现场恢复，可指定保存/恢复对象，并可对「Agent 操作对象（工作区文件）」用独立 Git 仓库管理，与用户 .git 完全解耦。

---

## 一、目标与范围

### 1.1 能力目标

- **现场保存**：将当前运行现场（或选定子集）保存为 Checkpoint，得到唯一 `checkpoint_id`，可持久化或仅内存。
- **现场恢复**：根据 `checkpoint_id` 将已保存的现场写回当前运行时，使执行可从该现场继续。
- **可指定对象**：调用方指定哪些「组件」参与本次保存、哪些参与本次恢复（白名单）。
- **按对象开关**：每个组件可独立设置「是否参与保存」「是否参与恢复」（如只保存 STM+工作区文件、只恢复 STM）。

### 1.2 与现有能力的关系

- **IPlanAttemptSandbox**：保留，仍负责里程碑内 STM 快照/回滚/提交，不替代。
- **IExecutionControl.checkpoint(label, payload)**：保留，用于 HITL 暂停点；Checkpoint 可在 pause 时额外做一次「现场保存」并记入 event log。
- **Task.resume_from_checkpoint**：恢复时由调用方传入 `resume_from_checkpoint=checkpoint_id`，Session 初始化后先 `restore(checkpoint_id, scope)` 再进入循环。

---

## 二、参与保存/恢复的「对象」（组件键）

可参与保存/恢复的组件用**组件键**表示，例如：

| 组件键 | 含义 |
|--------|------|
| `stm` | 短期记忆（对话流等） |
| `session_state` | 会话状态（milestone 列表、当前索引等） |
| `session_context` | 会话上下文（config 快照、session_id 等） |
| `config` | 有效配置快照 |
| `plan_state` | 当前 ValidatedPlan / 当前 milestone 索引等 |
| `budget` | 预算使用情况 |
| `workspace_files` | 工作区中由 Agent 修改/新增的文件（见下文「工作区文件」） |

**CheckpointScope** 为每个组件键提供：

- `include_in_save`：该对象是否参与本次 save。
- `include_in_restore`：该对象是否参与本次 restore。

支持预设（如 all、stm_only、stm_and_session、stm_and_workspace）和自定义组合。

---

## 三、工作区文件（Agent 操作对象）— 用 Git 管理

### 3.1 原则

- 不拷贝文件、不建「DARE 专用工作目录」再同步。
- Agent 使用**独立 Git 仓库**，与用户 `.git` **完全解耦**；所有 Git 操作由框架自动完成，用户无感。

### 3.2 核心：仓库与工作区解耦

Git 的**仓库（--git-dir）**和**工作区（--work-tree）**是解耦的：

- **仓库**：版本数据库，可放在任意路径（此处为 `.dare/agent.git`）。
- **工作区**：要管理的文件所在目录，由执行命令时的 `--work-tree` 指定（此处为工程根 `.`）。
- **管理范围**与「仓库所在目录层级」无关，只与 `--git-dir`、`--work-tree` 有关。因此 **`.dare/agent.git` 作为子目录，可以管理上级工程根目录的所有文件**。

### 3.3 目录与约定

- **用户仓库**：`<工程根>/.git`，用户照常使用，框架不触碰。
- **Agent 仓库**：`<工程根>/.dare/agent.git`，裸仓（`git init --bare`），仅用于 Checkpoint。
- **工作区**：两者都视「工程根」为工作区；Agent 通过每次命令显式指定 `--work-tree=.` 绑定工程根，无需移动用户 `.git`，也无须 worktree add。

### 3.4 排除规则（避免循环与误跟踪）

在 Agent 仓中通过 **excludesfile**（或等价 .gitignore）排除：

- `.git/` — 用户的 Git，不纳入 Agent 版本。
- `.dare/` — 框架目录（含 agent.git 自身），不纳入，避免循环。

仅跟踪工程根下的业务文件（src/、config/、requirements.txt 等）。

### 3.5 关键命令（均由框架封装）

**保存 Checkpoint（工作区文件部分）**

```bash
git --git-dir=.dare/agent.git --work-tree=. add -A
git --git-dir=.dare/agent.git --work-tree=. commit -m "DARE Checkpoint: <checkpoint_id>"
# 将返回的 commit_sha 记入 checkpoint 的 workspace_files 段
```

**恢复 Checkpoint（工作区文件部分）**

```bash
git --git-dir=.dare/agent.git --work-tree=. checkout -f <commit_sha> .
```

- `<commit_sha>`：checkpoint 中保存的 commit。
- 最后的 `.` 表示将历史快照覆盖到工作区当前目录（工程根）；`-f` 强制覆盖。
- 用户的 `.git` 未被 Agent 跟踪，checkout 不会动它。

**清理未跟踪文件（可选）**

```bash
git --git-dir=.dare/agent.git --work-tree=. clean -fdq -e .git -e .dare
```

- 删除 Agent 新增的、未跟踪的临时文件；`-e .git -e .dare` 排除用户仓和框架目录。

### 3.6 初始化（框架自动）

- 若不存在 `.dare/agent.git`：创建 `.dare/`，执行 `git --git-dir=.dare/agent.git init --bare`，配置 excludesfile 排除 `.git/`、`.dare/`，可选配置 `user.name`/`user.email` 为框架标识。

---

## 四、接口与类型（设计要点）

### 4.1 CheckpointScope

- 表达「本次 save/restore 涉及哪些组件」及每个组件的 `include_in_save` / `include_in_restore`。
- 支持预设（如 `ScopePresets.ALL`、`ScopePresets.STM_AND_WORKSPACE`）和按组件键自定义。

### 4.2 ICheckpointSaveRestore

- `save(scope: CheckpointScope, ..., context: 运行时上下文) -> str`  
  按 scope 采集选定组件状态，序列化为 Checkpoint，写入 Store（若配置），返回 `checkpoint_id`。  
  若 scope 含 `workspace_files`，则在工程根执行上述 Git 命令，将 commit_sha 写入 Checkpoint。
- `restore(checkpoint_id: str, scope: CheckpointScope, ..., context: 运行时上下文) -> None`  
  从 Store 加载 Checkpoint，按 scope 的恢复范围写回各组件。  
  若 scope 含 `workspace_files`，则从 Checkpoint 取 commit_sha，在工程根执行 checkout。

### 4.3 ICheckpointContributor

- 每个参与组件实现一个 Contributor：  
  - **serialize**：从当前运行时采集该组件数据，返回可序列化结构。  
  - **deserialize_and_apply**：从 Checkpoint 中该组件的数据写回当前运行时。
- 引擎按 scope 调用对应 Contributor；`workspace_files` 的 Contributor 内部通过 Git 命令（或封装好的 Git 客户端）完成 save/restore，不落盘文件内容到 Checkpoint payload（只存 commit_sha）。

### 4.4 ICheckpointStore（可选）

- 持久化抽象：`put(checkpoint_id, payload)`、`get(checkpoint_id)`、`delete(checkpoint_id)`。
- 默认实现：内存 dict；可选实现：文件系统（如 `.dare/checkpoints/<id>.json` 或目录）。  
- `workspace_files` 不把文件内容存 Store，只存 `git_commit`；Store 中 Checkpoint 的 payload 仅含各组件序列化结果及 `workspace_files: { "git_commit": "<sha>" }`。

---

## 五、与运行时的集成

- **Builder**：可注入 `ICheckpointSaveRestore`、`CheckpointScope` 预设、可选 `ICheckpointStore`；若启用 `workspace_files`，确保工程根可访问且可初始化 `.dare/agent.git`。
- **Agent 编排层**：在适当时机调用 save（如显式 API、或 pause 时可选自动 save）；恢复时若 `Task.resume_from_checkpoint` 存在则调用 `restore(checkpoint_id, scope)` 再进入 Session/Milestone 循环。
- **workspace_dir**：从 Config 或 SessionContext 获取，作为 `--work-tree` 的基准（通常为 `.` 时的当前工作目录）。

---

## 六、实现任务概要

1. **类型与接口**：定义 `CheckpointScope`、`ICheckpointSaveRestore`、`ICheckpointContributor`、`ICheckpointStore`。
2. **默认实现**：STM、SessionState、SessionContext（及可选 config、plan_state、budget）的 Contributor；默认 SaveRestore 按 scope 调用 Contributor 并写入 Store；内存 Store 与可选文件 Store。
3. **workspace_files**：实现基于 Git 的 Contributor（封装 `--git-dir=.dare/agent.git --work-tree=.` 的 add/commit/checkout）；Agent 仓初始化与 excludesfile 配置。
4. **集成**：Builder 注入、编排层 save/restore 调用、`resume_from_checkpoint` 处理。
5. **文档与测试**：单元测试（save 后 restore 状态一致；workspace_files 回滚后文件内容一致）。

---

## 七、总结

- **现场保存/恢复**：通过 CheckpointScope 指定对象，SaveRestore + Contributor + Store 完成采集与写回。
- **工作区文件**：用独立 Git 仓 `.dare/agent.git` + `--work-tree=.` 直接管理工程根，不拷贝、不碰用户 `.git`，用户无感；所有 Git 操作由框架封装。
- **两套 .git 各管各的**：用户用 `.git`，Agent 用 `.dare/agent.git`，通过 excludesfile 和显式 `--work-tree` 实现完全解耦。

以上为讨论后的完整计划，实现时以本目录下此文档为准。
