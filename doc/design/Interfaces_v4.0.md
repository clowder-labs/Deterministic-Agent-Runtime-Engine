# DARE Framework v4.0 接口设计（Draft，package = dare_framework）

> 状态：草案（用于评审）
>
> 本文给出 v4.0 的目标接口面：domain / types / stable interfaces（Kernel contracts）/ pluggable components / managers。
>
> 证据与可追溯：见 `doc/design/DARE_v4.0_evidence.yaml`。

---

## 0. 分域目录结构约定

每个 domain SHOULD 遵循：

```
dare_framework/<domain>/
  types.py
  interfaces.py
  components.py      # 可选（可插拔/组合接口位）
  __init__.py
  _internal/         # 可选（默认实现；不稳定；不作为公共 API）
```

推荐依赖规则：
- `types.py` MUST NOT 依赖 `components.py` 或 `_internal/`
- `interfaces.py` SHOULD 只依赖 `types.py`
- `components.py` MAY 依赖其他域的 `interfaces.py`（表达组合）

---

## 1. agent

### 1.1 `agent/interfaces.py`

```python
from __future__ import annotations

from typing import Any, Protocol

from dare_framework.plan.types import Task, RunResult


class IAgent(Protocol):
    """框架对外最小运行面。"""

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        """执行任务并返回 RunResult。

        约束：
          - deps MUST NOT 写入 Task（保持 Task 可序列化与审计友好）。
        """

        ...
```

### 1.2 可选：编排策略位

如果希望“一个 Agent facade + 可插拔编排策略”，可以增加：

```python
from __future__ import annotations

from typing import Any, Protocol

from dare_framework.plan.types import Task, RunResult


class IAgentOrchestration(Protocol):
    """一种编排实现（五层循环只是其中之一）。"""

    async def execute(self, task: Task, deps: Any | None = None) -> RunResult:
        ...
```

---

## 2. context（上下文工程）

> 本节以 `dare_framework3_4` 的 context-centric 设计为准：Context 是核心实体，messages 在每次模型调用前 request-time 组装。

### 2.1 `context/types.py`（核心类型）

建议最小集合：
- `Message`：统一消息格式（role/content/name/metadata）
- `Budget`：资源预算（max_* + used_*）
- `AssembledContext`：单次模型调用的 request-time 上下文（messages + tools + metadata）

### 2.2 `context/interfaces.py`（核心稳定契约）

```python
from __future__ import annotations

from typing import Any, Protocol


class IRetrievalContext(Protocol):
    """统一检索接口（STM/LTM/Knowledge 等实现该接口）。"""

    def get(self, query: str = "", **kwargs: Any) -> list["Message"]:
        ...


class IContext(Protocol):
    """Context-centric 核心实体。

    语义：
      - messages 不作为长期字段存储，而是每次调用前 assemble() 临时组装。
      - budget 与 external retrieval refs 挂在 Context 上，便于审计与复验。
    """

    # Fields
    id: str
    budget: "Budget"
    config: dict[str, Any] | None

    short_term_memory: IRetrievalContext
    long_term_memory: IRetrievalContext | None
    knowledge: IRetrievalContext | None

    toollist: list[dict[str, Any]] | None

    # Short-term memory methods
    def stm_add(self, message: "Message") -> None: ...
    def stm_get(self) -> list["Message"]: ...
    def stm_clear(self) -> list["Message"]: ...

    # Budget methods
    def budget_use(self, resource: str, amount: float) -> None: ...
    def budget_check(self) -> None: ...
    def budget_remaining(self, resource: str) -> float: ...

    # Tool listing (for Prompt.tools)
    def listing_tools(self) -> list[dict[str, Any]]: ...

    # Assembly (core)
    def assemble(self, **options: Any) -> "AssembledContext": ...

    # Config
    def config_update(self, patch: dict[str, Any]) -> None: ...
```

补充语义（v4 关键约束）：
- tool defs 的来源必须可追溯到 `IToolGateway.list_capabilities()` 的可信 registry（同源可信）。
- （可选兼容）如果某模型需要“文本化的 tool catalog”，由 adapter/策略层渲染，不作为 Context 的必选语义。

---

## 3. tool（能力模型 + 系统调用边界）

### 3.1 Canonical capability

`CapabilityDescriptor` 描述任意可调用能力：
- TOOL / AGENT / UI

### 3.2 `tool/interfaces.py`（稳定边界）

```python
from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.plan.types import Envelope
from dare_framework.tool.types import CapabilityDescriptor, ExecutionSignal


class IToolGateway(Protocol):
    """系统调用边界：所有外部副作用必须经由 invoke。"""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Envelope) -> Any: ...

    def register_provider(self, provider: object) -> None: ...


class IExecutionControl(Protocol):
    def poll(self) -> ExecutionSignal: ...

    def poll_or_raise(self) -> None: ...

    async def pause(self, reason: str) -> str: ...

    async def resume(self, checkpoint_id: str) -> None: ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str: ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None: ...
```

### 3.3 `tool/components.py`（providers / adapters / tools）

```python
from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework.tool.types import CapabilityDescriptor, RunContext, ToolResult


@runtime_checkable
class IToolProvider(Protocol):
    """为 Context.assemble 提供结构化 tool defs（Prompt.tools）。"""

    def list_tools(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class ITool(Protocol):
    @property
    def name(self) -> str: ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult: ...


class ICapabilityProvider(Protocol):
    async def list(self) -> list[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object: ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    @property
    def protocol_name(self) -> str: ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None: ...

    async def disconnect(self) -> None: ...

    async def discover(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any], *, timeout: float | None = None) -> Any: ...
```

### 3.4 可信 metadata 约定（建议）

`CapabilityDescriptor.metadata` 推荐保留：
- `risk_level`: string enum
- `requires_approval`: bool
- `timeout_seconds`: int
- `is_work_unit`: bool
- `capability_kind`: `tool` / `skill` / `plan_tool` / `agent` / `ui`

安全规则：
- 上述字段必须来自可信 registry（gateway/providers），不能来自模型/规划器输出。

---

## 4. plan（任务、计划、结果）

### 4.1 Proposed vs Validated

- Proposed plan/steps：不可信（来自 planner）
- Validated plan/steps：可信（来自 validator + registry 派生）

并且必须满足：Plan Attempt Isolation（失败计划不得污染外层状态）。

### 4.2 策略接口（`plan/components.py`）

- `IPlanner.plan(ctx) -> ProposedPlan`
- `IValidator.validate_plan(plan, ctx) -> ValidatedPlan`
- `IValidator.verify_milestone(result, ctx) -> VerifyResult`
- `IRemediator.remediate(verify_result, ctx) -> str`

---

## 5. model（LLM 调用适配）

### 5.1 统一输入面

v4.0 标准化模型输入为：
- `Prompt(messages + trusted tool defs + metadata)`

规则：
- tool defs 必须可追溯到 ToolGateway 的可信 registry。
- （可选）对不支持结构化 tools 的模型：可由 adapter/策略层渲染 tool catalog system message（审计友好）。

### 5.2 Adapter 接口（`model/components.py`）

- `IModelAdapter.generate(prompt, options=None) -> ModelResponse`

---

## 6. security（Trust + Policy + Sandbox）

`security/interfaces.py`：
- `verify_trust`：派生可信输入（含风险字段）
- `check_policy`：ALLOW/DENY/APPROVE_REQUIRED
- `execute_safe`：沙箱执行包装

---

## 7. event（审计与重放）

`event/interfaces.py`：
- append-only WORM
- query + replay
- 可选 hash-chain verify

---

## 8. hook（生命周期扩展点）

`hook/interfaces.py`：
- `IExtensionPoint.register_hook(...)`
- `IExtensionPoint.emit(...)`

默认语义建议：best-effort（hook 失败不应默认导致运行崩溃）。

---

## 9. config（配置与 managers）

- `IConfigProvider`：提供 effective config + reload
- managers（Layer 3）负责确定性装配：
  - discovery（entrypoints）
  - selection（single-select vs multi-load）
  - filtering（enable/disable/allowlists）
  - ordering（稳定 `order`）
  - instantiation

Kernel 不依赖 entrypoints discovery。

---

## 10. memory / knowledge（统一检索面 + 组合接口位）

- `memory` 与 `knowledge` 应实现 `IRetrievalContext`。
- 当某 domain 既要 retrieval 又要 callable capability 时，使用 `components.py` 做组合接口。

例：
- `IKnowledgeTool = IKnowledge + ITool`

---

## 11. Plan Tool（控制类工具）

规则：
- Execute 遇到 Plan Tool 必须中止执行并返回外层（Milestone/Plan）触发 re-plan。

推荐：
- 通过可信 registry metadata 标记 `capability_kind=plan_tool`。
- 兼容：允许 `plan:` 前缀约定。
