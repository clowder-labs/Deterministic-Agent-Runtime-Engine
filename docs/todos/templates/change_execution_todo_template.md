# <Change Title> Execution TODO

> 日期：YYYY-MM-DD
> Change ID：`<change-id>`
> 对应 OpenSpec：`openspec/changes/<change-id>/`
> 状态：`active` / `blocked` / `archived`

## 0. 使用规则

- 本文档是 active change 的详细协作板，不替代外层 `Claim Ledger`。
- 外层 ownership 先写在对应 TODO 文档；本板负责 change 内部的 work package、Gate、Touch Scope 与证据。
- 默认原则：`大包认领，小 task 验收`。
- `WP` 是认领单位；子任务只用于验收、回写、证据映射。
- 只有在设计文档、gap analysis、OpenSpec artifacts 入库后，才允许 `claimed/doing`。
- 本板若作为开工依据，必须随 docs-only `intent PR` 一起合入 `main`；intent PR 合入前不得开始实现代码。
- 共享契约必须先 Gate 冻结，再放行下游并行开发。

## 1. 上下文与边界

- 目标：
  - `<一句话说明这轮 change 要解决什么>`
- 不在范围：
  - `<明确不做什么>`
- 输入基线：
  - `docs/design/...`
  - `docs/todos/..._gap_analysis.md`
  - `openspec/changes/<change-id>/proposal.md`
  - `openspec/changes/<change-id>/design.md`
  - `openspec/changes/<change-id>/tasks.md`

## 2. Gate 冻结总览

| Gate | 冻结内容 | Producer | Consumer | 状态 | Evidence |
|---|---|---|---|---|---|
| Gate-1 | `<schema/payload/enum>` | `<WP-A>` | `<WP-B/WP-C>` | `todo` | `<PR/doc/test>` |
| Gate-2 | `<assemble/loop/policy>` | `<WP-B>` | `<WP-D>` | `todo` | `<PR/doc/test>` |
| Gate-3 | `<audit/log/state>` | `<WP-C>` | `<WP-D>` | `todo` | `<PR/doc/test>` |

## 3. Work Package 协作板

| WP | Goal | Owner | Depends On | Touch Scope | Freeze Gate | Status | Branch/Worktree | PR | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|---|---|---|
| WP-A | `<独立目标>` | `<name>` | `-` | `<dirs/files>` | `Gate-1` | `todo` | `<branch>` | `<pr>` | `<tests/docs>` | `YYYY-MM-DD` |
| WP-B | `<独立目标>` | `<name>` | `WP-A` | `<dirs/files>` | `Gate-2` | `todo` | `<branch>` | `<pr>` | `<tests/docs>` | `YYYY-MM-DD` |
| WP-C | `<独立目标>` | `<name>` | `Gate-1` | `<dirs/files>` | `Gate-3` | `todo` | `<branch>` | `<pr>` | `<tests/docs>` | `YYYY-MM-DD` |
| WP-D | `<独立目标>` | `<name>` | `Gate-2, Gate-3` | `<dirs/files>` | `Gate-4` | `todo` | `<branch>` | `<pr>` | `<tests/docs>` | `YYYY-MM-DD` |

状态建议：

- `todo -> claimed -> doing -> review -> done`
- `todo/claimed/doing -> blocked -> doing/dropped`

拆包规则：

- 单个 WP 推荐 0.5-2 天闭环。
- 若跨 2 个以上 Gate，拆包。
- 若两个人会改同一组共享契约，改成“先上游冻结，后下游实现”。

## 4. 子任务验收表

### WP-A

| Task ID | Related Gap / OpenSpec | Description | Status | Evidence |
|---|---|---|---|---|
| A-1 | `<GAP-001 / 1.1>` | `<验收点>` | `todo` | `<test/doc>` |
| A-2 | `<GAP-002 / 1.2>` | `<验收点>` | `todo` | `<test/doc>` |

### WP-B

| Task ID | Related Gap / OpenSpec | Description | Status | Evidence |
|---|---|---|---|---|
| B-1 | `<GAP-003 / 2.1>` | `<验收点>` | `todo` | `<test/doc>` |
| B-2 | `<GAP-004 / 2.2>` | `<验收点>` | `todo` | `<test/doc>` |

### WP-C

| Task ID | Related Gap / OpenSpec | Description | Status | Evidence |
|---|---|---|---|---|
| C-1 | `<GAP-005 / 3.1>` | `<验收点>` | `todo` | `<test/doc>` |

## 5. 接口兼容性矩阵

| 接口项 | 生产方 | 消费方 | 冲突风险 | 冻结时点 |
|---|---|---|---|---|
| `<schema-a>` | `WP-A` | `WP-B/WP-C` | `<字段名或语义漂移>` | `Gate-1` |
| `<payload-b>` | `WP-B` | `WP-D` | `<序列化或事件顺序冲突>` | `Gate-2` |
| `<decision-c>` | `WP-C` | `WP-D` | `<日志/审计字段不一致>` | `Gate-3` |

## 6. 联调与收口

- 联调入口：
  - `<command/test suite>`
- 完成条件：
  - `<端到端通过条件>`
  - `<文档回写条件>`
  - `<OpenSpec tasks 完成条件>`

## 7. 维护约定

- Owner 变化、状态变化、PR 变化当天回写。
- `review` 前必须补证据。
- `done` 前必须确认 execution board 与 OpenSpec `tasks.md` 一致。
- 归档时补最终结论，并迁移到 `docs/todos/archive/` 或标记 `archived`。
