# Agent Development Rules (Mandatory)

These rules apply to all agent-generated changes in this repository.

## Agent 开发强制规则
1. 只改与任务直接相关文件，禁止顺手重构与无关优化。
2. 一个 PR 只做一件事，超出范围必须拆分。
3. 不得修改公共接口/数据结构，除非任务明确且给出影响分析。
4. 必须补测试或更新测试，并附上本地/CI 的测试证据。
5. 任何跳过测试（skip/only/exclude）必须说明理由并经过 review。

## Operating Notes
- Keep diffs small to reduce merge conflicts in multi-agent parallel work.
- If a change is risky, split it into follow-up PRs instead of broad refactors.
- Prefer adding new files over editing large existing files when possible.
