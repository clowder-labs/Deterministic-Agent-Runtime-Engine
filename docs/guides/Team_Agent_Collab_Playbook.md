# Team Agent 协作手册（Worldline Convergence v1）

> 适用对象：本仓库所有并行开发成员（含各类 Agent）。
> 目标：在高速并行提交下，保持 `main` 只有一条可验证世界线。

## 1. 我们的协作底线（必须）

1. `main` 只允许通过 PR 合并，禁止直推。
2. 一个 PR 只做一件事（One PR One Thing）。
3. 禁止顺手重构、全仓格式化、无关文件改动。
4. 改动必须附测试证据（本地或 CI）。
5. 任何 `skip/only/exclude` 必须说明理由并经 review。

对应规则来源：
- `/Users/lysander/projects/dare-framework/docs/agent_rules.md`
- `/Users/lysander/projects/dare-framework/.github/pull_request_template.md`

## 2. 日常工作流（每次都按这个走）

1. 同步主干：`git fetch origin --prune`
2. 从最新 `origin/main` 开分支：`codex/<topic>` 或 `feature/<topic>`
3. 小步提交，确保每次提交可解释。
4. 开 PR，并完整填写模板全部字段。
5. 等 CI 绿灯后再合并，不抢跑。

建议本地最小自检命令：

```bash
python -m pip install -r requirements.txt
ruff check dare_framework tests --select E9,F63,F7
python -m compileall -q dare_framework tests
pytest -q tests/smoke -m smoke
./scripts/ci/run_risk_matrix.sh
./scripts/ci/check_test_skip_markers.sh
./scripts/ci/check_lockfile_policy.sh
```

## 3. 当前 CI 闸门说明（按阶段）

工作流：
- `/Users/lysander/projects/dare-framework/.github/workflows/ci-gate.yml`

当前检查项：
- `lint`
- `build`
- `smoke-tests`（阶段性观察，后续可转 required）
- `risk-matrix`
- `test-skip-guard`
- `lockfile-policy`

治理配置说明：
- `/Users/lysander/projects/dare-framework/docs/governance/branch-protection.md`

## 4. 免费版主干护栏（main-guard）

工作流：
- `/Users/lysander/projects/dare-framework/.github/workflows/main-guard.yml`

触发：
- 每次 `push` 到 `main`

行为：
1. 检测该次推送中的 commit 是否关联 PR 元数据。
2. 若发现疑似直推，自动创建 incident issue。
3. `MAIN_GUARD_MODE=revert-pr` 时，自动创建回滚 PR。
4. 该次 `main-guard` run 标红留痕。

仓库变量（已支持）：
- `MAIN_GUARD_MODE`: `revert-pr` 或 `alert-only`
- `MAIN_GUARD_ALLOW_ACTORS`: 紧急允许直推的 actor 白名单（逗号分隔）
- `MAIN_GUARD_ALLOW_MARKER`: 提交信息绕过标记（默认 `[main-guard:allow-direct-push]`）

## 4.1 合并人工审批护栏（manual-merge-guard）

工作流：
- `/Users/lysander/projects/dare-framework/.github/workflows/manual-merge-guard.yml`

作用：
1. PR 合入 `main` 后检查是否符合人工审批策略。
2. 默认把“作者自合并”视为违规（`author == merged_by`）。
3. 必须存在至少一个独立 `APPROVED` review。
4. 违规时自动发 incident，必要时自动回滚 PR。

仓库变量：
- `MANUAL_MERGE_GUARD_MODE`: `revert-pr` 或 `alert-only`
- `MANUAL_MERGE_GUARD_ALLOW_MERGERS`: 紧急白名单（逗号分隔）

## 5. 冲突最小化策略（并行开发必做）

1. 小 PR：尽量控制在一个目标、少文件、少行数。
2. 新增优先：优先新增文件，不大面积改历史文件。
3. 目录归属清晰：跨模块改动必须写影响分析。
4. 锁文件有纪律：lockfile 改动必须同 PR 同步 manifest。
5. 风险路径强约束：鉴权/并发/执行控制改动必须带 `risk-matrix` 证据。

## 6. Docs 组织规范（队友新增文档时）

1. 面向流程/操作的文档放在 `docs/guides/`。
2. 面向架构真相的文档放在 `docs/design/`，保持“权威文档唯一”。
3. 过时资料必须归档到 `docs/design/archive/`，避免多版本并存混淆。
4. 新增文档后，至少在一个入口文档里补链接（`CONTRIBUTING.md` 或 `docs/README.md`）。

## 7. 异常处理 SOP

场景 A：CI 红灯
1. 先看失败 job 日志，不要盲改。
2. 只改与失败直接相关内容。
3. 修复后在 PR 描述补“根因 + 修复点 + 验证证据”。

场景 B：发现疑似直推 `main`
1. 先看 `main-guard` run 与 incident issue。
2. 若自动回滚 PR 已创建，优先审阅并尽快合并。
3. 若是紧急合法直推，补 postmortem，并在后续 PR 说明原因。

场景 C：并发冲突严重
1. 暂停大改，先把主干拉齐。
2. 把大 PR 拆成多个小 PR（按模块或按阶段拆）。
3. 先合并治理类 PR，再合并功能类 PR。

## 8. 推荐执行节奏（每周）

1. 周一：确认 required checks 与主干策略是否符合当前阶段。
2. 周中：抽样检查 2-3 个 PR 的模板填写和测试证据质量。
3. 周末：复盘 main-guard incident，收紧或放宽变量策略。

## 9. 给 Opus 的协作命令（可选）

如果我们希望让 Opus 协助润色这份手册，可直接发：

```text
请基于以下仓库现状，帮我们把 Team Agent 协作手册润色为 v2：
1) 不改变当前流程约束（PR-only, CI gates, main-guard）。
2) 提升可读性，增加“新同学首日上手清单”与“常见误区”。
3) 保持可执行，避免空泛原则。
4) 输出为 Markdown，覆盖原文件 docs/guides/Team_Agent_Collab_Playbook.md。
```

---

维护约定：
- Owner: 平台治理负责人（可轮值）
- 变更方式：PR 更新，必须在 PR 描述中写明“为什么要改这条规则”
