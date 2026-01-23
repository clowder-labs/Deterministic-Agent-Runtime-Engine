## 1. Proposal → Apply checklist (implementation happens after approval)

- [x] 1.1 Add v4-style domain scaffolding files to `dare_framework3_4/` (types/kernel/interfaces/_internal).
- [x] 1.2 Define/align interface declarations (Protocols + types) per `doc/design/Interfaces_v4.0.md` for:
  - agent (IAgent)
  - context (Message/Budget/AssembledContext + IContext/IRetrievalContext)
  - tool (IToolGateway/IExecutionControl + IToolProvider)
  - model (IModelAdapter + Prompt/ModelResponse/GenerateOptions)
  - memory/knowledge (IRetrievalContext implementers)
  - plan/security/event/hook/config (placeholders; minimal)
- [x] 1.3 Rename legacy `internal/` → `_internal/` and update all internal imports accordingly.
- [x] 1.4 Fix `dare_framework3_4/tool/_internal/__init__.py` so it does not import missing modules (remove invalid exports; add placeholders only if required).
- [x] 1.5 Update `doc/design/DARE_v4.0_evidence.yaml` source paths for any moved v3.4 evidence files.

## 2. Validation
- [x] 2.1 Run `python -m compileall dare_framework3_4` (import/parse sanity).
- [x] 2.2 Run focused tests/examples if present (at minimum: imports for `examples/basic-chat/chat3.4.py` dependencies).
- [x] 2.3 Run `openspec validate align-framework3-4-layout --strict`.
