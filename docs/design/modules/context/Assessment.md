# Context Domain Assessment

> Status: draft (2026-02-05). Scope: `dare_framework/context` (including memory/knowledge integration notes).

## 1. Scope & Responsibilities

- Hold session context references (STM/LTM/Knowledge + Budget).
- Assemble request‑time `AssembledContext` for model calls.
- Provide tool listing via injected tool provider/manager.
- Surface minimal data models used across domains (`Message`, `Budget`).

## 2. Current Public Surface (Facade)

`dare_framework.context` exports:
- Types: `Message`, `Budget`, `AssembledContext`
- Interfaces: `IContext`, `IRetrievalContext`
- Default implementation: `Context`

## 3. Actual Dependencies

- **Memory**: STM is expected to implement `add/clear/compress` (beyond `IRetrievalContext.get`).
- **Tool**: `_tool_provider` may be `IToolProvider` or `IToolManager` for `list_tool_defs`.
- **Skill**: current skill mounted and injected into system prompt at assemble time.
- **Model**: `AssembledContext.sys_prompt` carries `Prompt`.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Tool cache exposure (fixed)**
   - `toollist` was part of the interface but only used internally as a cache.
   - Moved to `_tool_list` (internal) to reduce public surface.

2. **Config mutability ambiguity**
   - `config_update` implied mutable config while spec calls for a snapshot.
   - Keep `config` attribute as optional snapshot; remove `config_update`.

3. **STM contract mismatch**
   - `IRetrievalContext` only defines `get`, but `Context` expects STM to support
     `add/clear/compress` (type‑ignored).
   - This is an architectural mismatch, not yet resolved in the kernel contract.

4. **Skill mount methods are not part of `IContext`**
   - `set_skill/clear_skill/current_skill` are internal usage points for agent
     skill flow. They are intentionally not part of the stable interface.

5. **Metadata minimums still undefined**
   - `AssembledContext.metadata` only carries `context_id`; tool snapshot hash
     and config hash remain TODOs.

## 5. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.context`**:
  - `IContext`, `IRetrievalContext`
  - `Message`, `Budget`, `AssembledContext`
  - `Context` as supported default (optional; can be moved behind a factory later)

- **Keep internal**:
  - `_tool_provider`, `_tool_list` cache
  - `_sys_prompt` and skill‑mount helpers

## 6. Doc Updates Needed

- `docs/design/modules/context/README.md`: reflect internal tool cache + config snapshot.
- `docs/design/Interfaces.md`: remove `toollist` and `config_update`.
- `DARE_FRAMEWORK_PPT_SOURCE.md`: align interface diagram with updated fields.

## 7. Proposed Implementation Plan (Context Domain)

1. Remove `toollist` from `IContext`; keep internal cache only.
2. Drop `config_update` and treat `config` as read‑only snapshot.
3. Replace string annotations with direct type refs.
4. Update docs + module index.

## 8. Open Questions

- Should STM capabilities (`add/clear/compress`) be formalized in a context‑local
  protocol to avoid `type: ignore`, or remain implied via memory domain?
- Do we want a formal `ContextFactory` to avoid exposing `Context` directly?

## 9. Memory / Knowledge Integration Notes (merged)

> Scope: `dare_framework/memory` + `dare_framework/knowledge` as Context dependencies.

### 9.1 Public Surface (current)

- `dare_framework.memory`: `IShortTermMemory`, `ILongTermMemory`, `LongTermMemoryConfig`, `create_long_term_memory`, `InMemorySTM`
- `dare_framework.knowledge`: `IKnowledge`, `IKnowledgeTool`, `KnowledgeConfig`, `create_knowledge`

### 9.2 Dependency Highlights

- Context defaults STM to `InMemorySTM` when not injected.
- Agent builder resolves LTM/Knowledge via factories from config.
- Knowledge capabilities are exposed as internal tools (`knowledge_get` / `knowledge_add`).
- Vector LTM/Knowledge depend on embedding adapter; missing adapter yields `None` from factory.

### 9.3 Additional Gaps

1. Retrieval kwargs contract is not standardized across implementations.
2. Cross-source dedup/ranking/conflict policy is not yet formalized at Context boundary.
3. Recall-quality and compression-loss observability is still missing.

### 9.4 Doc Sync

- Keep memory/knowledge integration details in `docs/design/module_design/context/README.md`.
