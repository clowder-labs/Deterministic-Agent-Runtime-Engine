## 1. Core skeleton + runtime flow (first milestone)
- [x] 1.1 Scaffold `dare_framework/` package layout and define core data models (Task, Milestone, RunContext, Envelope, DonePredicate, Plan, ValidatedPlan, ToolResult, RunResult, PolicyDecision, RuntimeState).
- [x] 1.2 Define core interfaces per UML A.1 and v1.1 (IRuntime, IEventLog, IToolRuntime, IPolicyEngine, IPlanGenerator, IValidator, IRemediator, ISkillRegistry, IContextAssembler, IModelAdapter, IToolkit, ITool, ISkill, IMemory, IHook, ICheckpoint).
- [x] 1.3 Implement LocalEventLog (append-only JSONL + hash chain) and file-backed ICheckpoint for observability/debugging.
- [x] 1.4 Implement AgentRuntime state machine and five-layer flow using small loop helpers (Plan/Execute/Tool) to avoid monolithic pseudocode while preserving v1.3 semantics.
- [x] 1.5 Provide minimal stub/default implementations for PolicyEngine, PlanGenerator, Validator, Remediator, ContextAssembler to enable deterministic flow with mocks.

## 2. Interface layer assembly
- [x] 2.1 Implement registries (ToolRegistry, SkillRegistry) and Toolkit surface.
- [x] 2.2 Implement ToolRuntime with policy checks, plan-tool detection, and envelope-aware Tool Loop entry.
- [x] 2.3 Implement AgentBuilder composition API with quick_start and component overrides.
- [x] 2.4 Define MCP interfaces (IMCPClient) and MCPToolkit stub; ensure no MCP config is required for default runtime.

## 3. Example coding agent
- [x] 3.1 Add MockModelAdapter and/or DeterministicPlanGenerator fixtures for deterministic runs.
- [x] 3.2 Wire `examples/coding-agent/` to AgentBuilder with a switch for mock vs real adapters.
- [x] 3.3 Add deterministic example tests covering a full run without network dependencies.

## 4. Validation
- [x] 4.1 Unit tests for runtime state transitions and event log hash-chain verification.
- [x] 4.2 Integration test for end-to-end flow using the example agent in deterministic mode.

## 5. Architecture refactor + MCP SDK integration (v1.3 alignment)
- [x] 5.1 Restructure `dare_framework/` into layered packages (core/components/validators/plugins) aligned to v1.3.
- [x] 5.2 Split default components into dedicated modules and update imports/builders.
- [x] 5.3 Update IMCPClient per v1.1 and implement MCP SDK-based clients (stdio/streamable-http).
- [x] 5.4 Add async MCP initialization path in AgentBuilder and document usage.
- [x] 5.5 Update `openspec/project.md` to reflect new structure and MCP SDK integration notes.
- [x] 5.6 Re-run tests under pyenv 3.12 and record results.

## 6. Merge impl_main_runtime model + rename package (dare_framework)
- [x] 6.1 Rename package to `dare_framework` and update all imports/tests/examples accordingly.
- [x] 6.2 Migrate core models to include Session/Milestone summaries and context objects from impl_main_runtime (SessionContext, MilestoneContext, SessionSummary, MilestoneSummary, Evidence, EnvelopeBudget, ValidatedStep).
- [x] 6.3 Update runtime flow to use Session/Milestone contexts, preserve five-layer loop behavior, and keep LocalEventLog hash chain.
- [x] 6.4 Reconcile interface definitions to include structured generation options and enforcement hooks while keeping MCP client surface.
- [x] 6.5 Merge or map example agent to new package name and richer model types; ensure deterministic mode still works.
- [x] 6.6 Update tests to cover new summaries/contexts and ensure existing flow tests still pass.
- [x] 6.7 Re-run tests under pyenv 3.12 and record results.

## Dependencies / Parallelism
- 1.x must complete before 2.x and 3.x.
- 2.4 can run in parallel with 2.1-2.3 once interfaces are defined.
- 4.x depends on 1-3.
