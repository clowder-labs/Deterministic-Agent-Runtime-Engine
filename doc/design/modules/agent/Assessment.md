# Agent Domain Assessment

> Status: draft (2026-02-04). Scope: `dare_framework/agent` only.

## 1. Scope & Responsibilities

- Provide the minimal execution surface (`IAgent.run`, `__call__`).
- Offer default agent implementations (SimpleChat, React, DareAgent).
- Orchestrate Context/Model/Tool/Plan/Hook/Event integration.
- Manage transport-backed execution loops (AgentChannel).
- Provide builders for deterministic agent assembly.

## 2. Current Public Surface (Facade)

`dare_framework.agent` exports:
- Interfaces: `IAgent`, `IAgentOrchestration`
- Types: `AgentDeps`
- Base class: `BaseAgent`
- Default implementations: `DareAgent`, `ReactAgent`, `SimpleChatAgent`
- Builders: `DareAgentBuilder`, `ReactAgentBuilder`, `SimpleChatAgentBuilder`

## 3. Actual Dependencies

- **Context**: STM + tool listing + optional skill injection.
- **Model**: `IModelAdapter.generate` for all modes.
- **Tool**: ToolGateway/ToolManager for invoke + tool loop.
- **Plan**: Planner/Validator/Remediator in five-layer mode.
- **Transport**: AgentChannel for poll/send/interrupt and hook streaming.
- **Event/Hook/Observability**: event log + hook emissions + telemetry.

## 4. Findings (Gaps / Overexposure / Mismatches)

1. **Transport loop semantics now internal**
   - `BaseAgent.start/stop` manage the loop; `run_interruptible` is used for interrupts.

2. **Builder typing fixed**
   - Builders now return concrete agent types instead of `Any`.

3. **Skill mode alignment is partial**
   - `skill_mode=search_tool` registers `search_skill`.
   - `skill_mode=agent` mounts `initial_skill_path` only; multi-skill orchestration is TBD.

4. **Public surface vs minimal surface**
   - Default agent classes remain exported for convenience; builders are still the preferred entry points.

## 5. Minimal Public Surface (Proposed)

- **Keep in `dare_framework.agent`**:
  - `IAgent`, `IAgentOrchestration`
  - Builders: `DareAgentBuilder`, `ReactAgentBuilder`, `SimpleChatAgentBuilder`
  - `BaseAgent` (if inheritance is supported)
  - Default agents (if treated as stable API)

## 6. Doc Updates Needed

- `doc/design/modules/agent/README.md`: reflect transport lifecycle + hook emissions.
- `doc/design/modules/hook/README.md`: reflect DareAgent integration.
- `doc/design/TODO_INDEX.md`: remove stale hook integration TODOs.

## 7. Proposed Implementation Plan (Agent Domain)

1. Keep transport loop internal; drive interrupts via `run_interruptible`.
2. Keep builders as preferred entry points; keep default agents public for now.
3. Align skill mode behavior with config (agent vs search_tool).

## 8. Open Questions

- Do we want to hide default agents from the facade in favor of builders only?
- When should multi-skill "agent mode" orchestration be implemented?
