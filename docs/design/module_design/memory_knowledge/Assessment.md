# Memory / Knowledge Domain Assessment

> Status: draft (2026-02-03). Scope: `dare_framework/memory` + `dare_framework/knowledge`.

## 1. Scope & Responsibilities

- Provide retrieval implementations for Context (STM/LTM/Knowledge).
- Expose stable interfaces for memory/knowledge components.
- Offer factory helpers to construct LTM/Knowledge from config.

## 2. Current Public Surface (Facade)

`dare_framework.memory` exports:
- Interfaces: `IShortTermMemory`, `ILongTermMemory`
- Types: `LongTermMemoryConfig`
- Factory: `create_long_term_memory`
- Default STM: `InMemorySTM`

`dare_framework.knowledge` exports:
- Interface: `IKnowledge`, `IKnowledgeTool`
- Types: `KnowledgeConfig`
- Factory: `create_knowledge`

## 3. Actual Dependencies

- **Context**: defaults to `InMemorySTM` if STM not provided.
- **Agent builder**: uses `create_long_term_memory` / `create_knowledge` based on config.
- **Tool**: knowledge is exposed via internal `knowledge_get` / `knowledge_add` tools.
- **Embedding**: vector memory/knowledge require `IEmbeddingAdapter`.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Memory defaults overexposed (mitigated)**
   - LTM concrete classes are no longer exported; use factory instead.

2. **Knowledge defaults overexposed (mitigated)**
   - Raw/vector knowledge implementations and raw storage are internal; use factory instead.

3. **Doc drift**
   - Prior docs claimed no default LTM/Knowledge; implementations exist.

## 5. Minimal Public Surface (Proposed)

- **Memory**:
  - Keep `IShortTermMemory`, `ILongTermMemory`, `LongTermMemoryConfig`, `create_long_term_memory`.
  - Keep `InMemorySTM` as the supported default STM.

- **Knowledge**:
  - Keep `IKnowledge`, `IKnowledgeTool`, `KnowledgeConfig`, `create_knowledge`.
  - Keep raw/vector implementations internal.

## 6. Doc Updates Needed

- `docs/design/module_design/memory_knowledge/README.md`: reflect default implementations + factory path.
- `docs/design/Framework_MinSurface_Review.md`: align memory/knowledge exposure lists.

## 7. Proposed Implementation Plan (Memory / Knowledge)

1. Move `InMemorySTM` to memory root and keep it public.
2. Keep LTM/Knowledge implementations internal; expose factories only.
3. Update examples to use factories instead of concrete classes.
