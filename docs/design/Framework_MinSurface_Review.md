# DARE Framework Minimal Surface Review (2026-02-03)

## 0. Goal
Minimize public API surface to reduce misuse and long‑term maintenance cost.
This review focuses on what each domain **should** expose publicly vs what should
be kept internal (`_internal`) or factory‑only.

## 1. Minimal Exposure Rules (Recommended)
1. **Kernel first**: only stable contracts live in `kernel.py` and are exported.
2. **Interfaces are optional**: expose only if intended for external injection.
3. **Types only when required**: export types that cross domain boundaries; keep
   helper DTOs internal.
4. **Implementations are not public** unless explicitly “default and supported.”
5. **Factories over classes**: export factory functions instead of concrete
   implementation classes when possible.

## 2. Domain‑by‑Domain Findings

For each domain:
- **Keep**: minimal public surface
- **Hide**: should move to `_internal` or be accessed through factory
- **Doc vs Impl**: whether the overexposure is a documentation gap or an
  implementation/export problem

### 2.1 Agent
**Current exports** (`dare_framework/agent/__init__.py`):
`IAgent`, `IAgentOrchestration`, `BaseAgent`, `DareAgent`, `ReactAgent`,
`SimpleChatAgent`, builders.

**Keep** (minimal):
- `IAgent`
- Builders (factory entry points): `DareAgentBuilder`, `ReactAgentBuilder`,
  `SimpleChatAgentBuilder`
- `DareAgent`, `ReactAgent`, `SimpleChatAgent` (default implementations)
- Optional: `BaseAgent` only if extension via inheritance is a supported pattern

**Hide** (internal):
- `AgentDeps` (unless it is part of stable API)

**Doc vs Impl**:
- **Doc gap**: docs should explicitly state “builders are the preferred entry
  points.”

### 2.2 Config
**Current exports**: Config types, `FileConfigProvider`, `build_config_provider`.

**Keep**:
- `Config` + config dataclasses
- `IConfigProvider`
- `build_config_provider`
- `FileConfigProvider` (default implementation)

**Hide**:
- `ComponentType` if it is already exposed elsewhere (avoid duplication)

**Doc vs Impl**:
- **Impl gap**: default implementation is exposed for convenience.

### 2.3 Context
**Current exports**: `Context`, `IContext`, `IRetrievalContext`, `Message`,
`Budget`, `AssembledContext`.

**Keep**:
- `IContext`, `IRetrievalContext`
- `Message`, `Budget`, `AssembledContext`
- Optional: `Context` as default implementation if officially supported

**Notes**:
- `Context` keeps an internal tool list cache; it is not part of the public contract.
- `config` is treated as a read‑only snapshot; no `config_update` in the interface.

**Hide**:
- If minimalism is strict, move `Context` behind a factory (e.g. `create_context`).

**Doc vs Impl**:
- **Impl gap**: public access to a mutable concrete class may cause tight
  coupling.

### 2.4 Embedding
**Current exports**: `IEmbeddingAdapter`, `EmbeddingOptions`, `EmbeddingResult`,
`OpenAIEmbeddingAdapter`.

**Keep**:
- `IEmbeddingAdapter`, `EmbeddingOptions`, `EmbeddingResult`

**Hide**:
- `OpenAIEmbeddingAdapter` (default implementation; should come from a factory
  or `embedding._internal`)

**Doc vs Impl**:
- **Impl gap**: default implementation exposed as public.

### 2.5 Event
**Current exports**: `IEventLog`, `Event`, `RuntimeSnapshot`.

**Keep**:
- `IEventLog`, `Event`, `RuntimeSnapshot`

**Hide**:
- None (already minimal)

**Doc vs Impl**:
- OK.

### 2.6 Hook
**Current exports**: `IHook`, `IExtensionPoint`, `HookFn`, `HookPhase`,
`IHookManager`, `HookExtensionPoint`.

**Keep**:
- `IHook`, `IExtensionPoint`, `HookPhase`
- Optional: `IHookManager` if it is intended for external integration

**Hide**:
- `HookExtensionPoint` (internal helper)
- `HookFn` if not required externally

**Doc vs Impl**:
- **Impl gap**: internal helper is exported.

### 2.7 Knowledge
**Current exports**: `IKnowledge`, `IKnowledgeTool`, `KnowledgeConfig`,
`create_knowledge`.

**Keep**:
- `IKnowledge`, `IKnowledgeTool`
- `KnowledgeConfig`
- `create_knowledge` (factory)

**Hide**:
- Concrete implementations: `VectorKnowledge`, `RawDataKnowledge`,
  `InMemoryRawDataStorage`
- Internal DTOs: `Document`
- Tools: `KnowledgeGetTool`, `KnowledgeAddTool` (internal to knowledge/tooling)

**Doc vs Impl**:
- **Impl gap**: defaults are intentionally kept internal.

### 2.8 Memory
**Current exports**: `IShortTermMemory`, `ILongTermMemory`, `InMemorySTM`,
`LongTermMemoryConfig`, `create_long_term_memory`.

**Keep**:
- `IShortTermMemory`, `ILongTermMemory`
- `LongTermMemoryConfig`
- `create_long_term_memory`

**Hide**:
- Concrete LTM implementations: `RawDataLongTermMemory`, `VectorLongTermMemory`

**Doc vs Impl**:
- **Impl gap**: default STM is exposed for convenience; LTM remains internal.

### 2.9 Model
**Current exports**: interfaces, types, factories, default adapters/loaders.

**Keep**:
- `IModelAdapter`
- `ModelInput`, `ModelResponse`, `GenerateOptions`, `Prompt`
- `IModelAdapterManager`, `IPromptLoader`, `IPromptStore`
- Factories: `create_default_model_adapter_manager`, `create_default_prompt_store`

**Hide**:
- `OpenAIModelAdapter`, `OpenRouterModelAdapter` (default impls)
- `BuiltInPromptLoader`, `FileSystemPromptLoader`, `LayeredPromptStore`
  (default implementations)

**Doc vs Impl**:
- **Impl gap**: default implementations are exposed as public surface.

### 2.10 Observability
**Current exports**: `ITelemetryProvider`, `ISpan`, types.

**Keep**:
- `ITelemetryProvider`, `ISpan`
- `TelemetryConfig`, `SpanKind`, `SpanStatus`

**Hide**:
- Optional: `RunMetrics`, `TokenUsage`, `GenAIOperation` if not required by
  external callers (these are internal aggregation details)

**Doc vs Impl**:
- **Doc gap**: clarify which metrics are public API vs internal.

### 2.11 Plan
**Current exports**: plan types, interfaces, default planner/remediator.

**Keep**:
- `Task`, `RunResult`, `Milestone`, `VerifyResult`
- `Envelope`, `DonePredicate`
- `ProposedPlan`, `ValidatedPlan` (if planners/validators are external)
- `IPlanner`, `IValidator`, `IRemediator` + managers

**Hide**:
- `DefaultPlanner`, `DefaultRemediator` (default impls)
- `ToolLoopRequest` (agent internal execution detail)

**Doc vs Impl**:
- **Impl gap**: default impls exported; internal DTOs exposed.

### 2.12 Security
**Current exports**: `ISecurityBoundary` + types.

**Keep**:
- `ISecurityBoundary`, `PolicyDecision`, `RiskLevel`, `SandboxSpec`, `TrustedInput`

**Hide**:
- None (already minimal)

**Doc vs Impl**:
- OK.

### 2.13 Skill
**Current exports**: interfaces, `Skill` (defaults live under `skill.defaults`).

**Keep**:
- `Skill`, `ISkill`, `ISkillTool`, `ISkillLoader`, `ISkillStore`, `ISkillSelector`

**Hide**:
- `FileSystemSkillLoader`, `KeywordSkillSelector`, `SkillStore`,
  `SkillSearchTool` (exposed under `skill.defaults`)

**Doc vs Impl**:
- **Impl gap**: default implementations exported as public API.

### 2.14 Tool
**Current exports**: huge surface; includes all default tools, control classes,
MCP adapters, etc.

**Keep**:
- Kernel: `ITool`, `IToolProvider`, `IToolGateway`, `IToolManager`
- Interfaces: `IExecutionControl`
- Types: `CapabilityDescriptor`, `ToolDefinition`, `ToolResult`, `Envelope`,
  `RunContext`, `RiskLevelName`, `CapabilityMetadata`, `CapabilityKind` (if used
  externally)
  - MCP/Skill interfaces should live in their own domains (`mcp`, `skill`)
- Supported defaults: `ToolManager` (re-export via `dare_framework.tool`)

**Hide**:
- Default implementations from the facade: `DefaultExecutionControl`,
  built‑in tools (`ReadFileTool`, `RunCommandTool`, etc.)
- MCP/Skill helpers: `MCPToolProvider` (mcp.defaults), `NoOpMCPClient` (mcp internal),
  `NoOpSkill` (skill internal)
- Internal helpers: `Checkpoint`, `FileExecutionControl`

**Doc vs Impl**:
- **Impl gap**: too many implementation details exposed.

### 2.15 Transport
**Current exports**: envelope types, channel interfaces, and concrete adapters.

**Keep**:
- `AgentChannel`, `ClientChannel`, `TransportEnvelope`, encoder/decoder types

**Hide**:
- `DefaultAgentChannel`, `DirectClientChannel`, `StdioClientChannel`,
  `WebSocketClientChannel` (move to `transport.adapters` or `transport._internal`)

**Doc vs Impl**:
- **Impl gap**: default adapters exposed as public API.

## 3. Recommended Next Steps
1. **Define explicit public surface** per domain (Kernel + minimal types).
2. **Move default implementations** out of domain facades (`__init__.py`).
3. **Add factories** to access defaults without exposing class symbols.
4. **Document the public surface** in each module README and `Interfaces.md`.

## 4. Risks If Not Reduced
- Tight coupling to concrete classes prevents safe refactors.
- External users rely on internal DTOs that must then be supported forever.
- Increased likelihood of breaking changes with each internal improvement.

## 5. Implementation Note (2026-03-04)
- T0-4 facade compliance batch moved public-domain `__init__.py` imports away from direct `._internal` references into explicit public export layers (`defaults.py`, `impl`, `adapters`).
- The following facades now import only public modules directly: `checkpoint`, `embedding`, `event`, `hook`, `plan`, `security`, `transport`.
- A regression rule was added in `tests/unit/test_package_initializers_facade_pattern.py` to block future direct `._internal` imports from public facades.
