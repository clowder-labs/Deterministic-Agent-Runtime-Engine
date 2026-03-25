---
feature_ids: [fix-context-set-skill]
topics: [context, skill, auto_skill_mode, bugfix]
doc_kind: feature
created: 2026-03-25
status: active
---

# fix-context-set-skill: Fix AttributeError crash in auto_skill_mode

> Status: active | Owner: tianyiliang

## Why

When `enable_skill_tool=True` (the default), the LLM can call `search_skill` to dynamically select a skill at runtime. After the tool returns, `execute_engine` invokes `DareAgent._mount_skill_from_result`, which calls `context.set_skill()`. However, neither `IContext` nor `Context` defines `set_skill`, causing an uncaught `AttributeError` that crashes the execute loop.

This means auto_skill_mode is completely broken — the only usable path is persistent_skill_mode (`enable_skill_tool=False`).

## What

- Add `set_skill(self, skill: Skill | None) -> None` to `IContext` (kernel.py) as an abstract method
- Add concrete implementation in `Context` (context.py)

## Acceptance Criteria

- [ ] AC-1: `IContext` declares `set_skill` abstract method (consistent with `set_tool_gateway` pattern)
- [ ] AC-2: `Context.set_skill()` sets `_sys_skill` field
- [ ] AC-3: `_mount_skill_from_result` no longer raises `AttributeError` when `enable_skill_tool=True`
- [ ] AC-4: Persistent skill mode (`enable_skill_tool=False`) is unaffected

## Dependencies

None.

## Risk

Low — additive change only.

## Open Questions

None.

### Review and Merge Gate Links

- Intent PR: https://github.com/clowder-labs/Deterministic-Agent-Runtime-Engine/pull/228
- Implementation PR: https://github.com/clowder-labs/Deterministic-Agent-Runtime-Engine/pull/227
