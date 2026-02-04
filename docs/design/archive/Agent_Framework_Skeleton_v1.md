# 工业级 Agent 框架 - 骨架设计 v1.0

> 本文档把 v2.0-v2.4 的理念收敛成"能搭起来、能跑起来、能验证"的框架骨架。
> 不再讨论理念，只讨论：目录结构、接口定义、启动顺序、运行流程。

---

## 一、框架总览

### 1.1 一句话定位

```
一个 Plan→Execute→Verify 的 Agent 执行框架，
核心特点是：LLM 产出不可信，所有安全关键决策由系统派生和强制。
```

### 1.2 框架边界

```
框架负责：
✅ Agent 生命周期管理（初始化、运行、终止）
✅ 执行流程编排（Plan→Execute→Verify→Remediate）
✅ 工具注册与调用门禁
✅ 上下文装配与隔离
✅ 事件日志与证据链
✅ 策略检查与审批

框架不负责：
❌ 具体业务逻辑（由 Skills 提供）
❌ 具体工具实现（由 Tool 插件提供）
❌ 具体验证逻辑（由 Validator 插件提供）
❌ 模型选择策略（由 ModelRouter 插件提供）
```

### 1.3 目录结构

```
agent_framework/
├── core/                          # 核心框架代码
│   ├── __init__.py
│   ├── runtime.py                 # AgentRuntime 主循环
│   ├── state.py                   # RunState 状态模型
│   ├── events.py                  # 事件类型定义
│   └── errors.py                  # 错误分类
│
├── components/                    # 核心组件
│   ├── __init__.py
│   ├── model_adapter.py           # 模型适配器
│   ├── tool_registry.py           # 工具注册表
│   ├── tool_runtime.py            # 工具执行运行时
│   ├── policy_engine.py           # 策略引擎
│   ├── context_assembler.py       # 上下文装配器
│   ├── event_log.py               # 事件日志
│   └── evidence_factory.py        # 证据工厂
│
├── validators/                    # 验证器
│   ├── __init__.py
│   ├── trust_boundary.py          # 信任边界验证
│   ├── coverage_validator.py      # 覆盖率验证
│   ├── input_sanitizer.py         # 输入消毒
│   └── done_validator.py          # 完成验证
│
├── plugins/                       # 可插拔扩展
│   ├── tools/                     # 工具插件
│   ├── skills/                    # 技能插件
│   ├── models/                    # 模型插件
│   └── validators/                # 验证器插件
│
├── config/                        # 配置
│   ├── agent_config.yaml          # Agent 配置
│   ├── policy_config.yaml         # 策略配置
│   └── tool_contracts.yaml        # 工具契约配置
│
└── tests/                         # 测试
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 二、核心数据结构

### 2.1 状态模型（State Model）

```python
# core/state.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class RunPhase(Enum):
    """运行阶段"""
    INITIALIZING = "initializing"
    OBSERVING = "observing"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REMEDIATING = "remediating"
    COMPLETED = "completed"
    FAILED = "failed"


class TrustLevel(Enum):
    """信任级别"""
    SYSTEM = 4      # 系统（最高）
    DEVELOPER = 3   # 开发者
    USER = 2        # 用户
    LLM = 1         # LLM 产出（最低，不可信）
    RETRIEVED = 0   # 检索内容（不可信）


@dataclass
class Task:
    """任务输入"""
    task_id: str
    description: str                    # 用户描述
    expectations: List['Expectation']   # 验收期望（用户/系统提供，不是LLM）
    constraints: Dict[str, Any]         # 约束条件
    context: Dict[str, Any]             # 附加上下文
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Expectation:
    """验收期望 - 必须有结构化规格"""
    expectation_id: str
    description: str                    # 自然语言描述（供人阅读）
    priority: str                       # MUST / SHOULD / COULD
    verification_spec: 'VerificationSpec'  # 结构化验收规格（必填）


@dataclass
class VerificationSpec:
    """结构化验收规格"""
    type: str                           # test_pass / http_check / evidence_type / ...
    config: Dict[str, Any]              # 类型特定配置


@dataclass
class Plan:
    """计划 - LLM 产出，不可信"""
    plan_id: str
    task_id: str
    steps: List['PlanStep']
    created_by: str                     # 哪个模型生成的
    created_at: datetime
    trust_level: TrustLevel = TrustLevel.LLM  # 固定为 LLM，不可信


@dataclass
class PlanStep:
    """计划步骤 - LLM 产出，不可信"""
    step_id: str
    order: int
    description: str
    tool: str
    tool_input: Dict[str, Any]
    # 以下字段由 LLM 填写，但不被信任，会被 TrustBoundary 覆盖
    _llm_risk_level: Optional[str] = None
    _llm_rollback_possible: Optional[bool] = None


@dataclass
class ValidatedStep:
    """验证后的步骤 - 系统派生，可信"""
    step_id: str
    order: int
    description: str
    tool: str
    tool_input: Dict[str, Any]          # 已消毒
    # 以下字段从 ToolRegistry 派生，可信
    risk_level: 'RiskLevel'         # 从 Registry 派生
    requires_approval: bool             # 从 Registry 派生
    rollback_capable: bool              # 从 Registry 派生
    produces_assertions: List['Assertion']  # 从 Registry 派生
    trust_level: TrustLevel = TrustLevel.SYSTEM  # 系统派生，可信


@dataclass
class RunState:
    """运行状态 - 整个执行过程的状态"""
    run_id: str
    task: Task
    phase: RunPhase
    
    # 计划（LLM产出，不可信）
    current_plan: Optional[Plan] = None
    
    # 验证后的步骤（系统派生，可信）
    validated_steps: List[ValidatedStep] = field(default_factory=list)
    
    # 执行进度
    current_step_index: int = 0
    step_results: List['StepResult'] = field(default_factory=list)
    
    # 证据收集
    evidence_refs: List[str] = field(default_factory=list)
    
    # 验收结果
    verification_report: Optional['VerificationReport'] = None
    
    # 补救尝试
    remediation_count: int = 0
    max_remediations: int = 3
    
    # 时间戳
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    success: bool
    output: Any
    evidence_ref: Optional[str]         # 证据引用
    error: Optional['FailureInfo'] = None
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass
class FailureInfo:
    """失败信息"""
    code: str                           # 失败码
    message: str
    category: str                       # transient / permanent / policy_denied / needs_approval
    retryable: bool
    context: Dict[str, Any] = field(default_factory=dict)
```

### 2.2 事件类型

```python
# core/events.py

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class Event:
    """事件基类"""
    event_id: str
    event_type: str
    run_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    prev_hash: str = ""                 # 哈希链
    event_hash: str = ""                # 本事件哈希


# === 任务生命周期事件 ===

@dataclass
class TaskReceivedEvent(Event):
    """任务接收"""
    event_type: str = "task_received"
    task_id: str = ""
    task_description: str = ""
    expectations_count: int = 0


@dataclass
class RunStartedEvent(Event):
    """运行开始"""
    event_type: str = "run_started"
    agent_id: str = ""
    config_hash: str = ""               # 配置哈希（可复现）


@dataclass
class RunCompletedEvent(Event):
    """运行完成"""
    event_type: str = "run_completed"
    success: bool = False
    verification_passed: bool = False
    evidence_refs: list = field(default_factory=list)


# === 计划事件 ===

@dataclass
class PlanProposedEvent(Event):
    """计划提出（LLM产出，记录但不信任）"""
    event_type: str = "plan_proposed"
    plan_id: str = ""
    plan_hash: str = ""                 # 计划内容哈希
    model_used: str = ""


@dataclass
class PlanValidatedEvent(Event):
    """计划验证通过"""
    event_type: str = "plan_validated"
    plan_id: str = ""
    validated_steps_count: int = 0


@dataclass
class PlanRejectedEvent(Event):
    """计划被拒绝"""
    event_type: str = "plan_rejected"
    plan_id: str = ""
    rejection_reasons: list = field(default_factory=list)


# === 执行事件 ===

@dataclass
class StepStartedEvent(Event):
    """步骤开始"""
    event_type: str = "step_started"
    step_id: str = ""
    tool: str = ""
    input_hash: str = ""                # 输入哈希（不存原文）


@dataclass
class ToolInvokedEvent(Event):
    """工具调用"""
    event_type: str = "tool_invoked"
    step_id: str = ""
    tool: str = ""
    risk_level: str = ""
    approval_id: Optional[str] = None   # 如果需要审批


@dataclass
class StepCompletedEvent(Event):
    """步骤完成"""
    event_type: str = "step_completed"
    step_id: str = ""
    success: bool = False
    evidence_ref: Optional[str] = None


@dataclass
class StepFailedEvent(Event):
    """步骤失败"""
    event_type: str = "step_failed"
    step_id: str = ""
    failure_code: str = ""
    failure_category: str = ""


# === 验证事件 ===

@dataclass
class VerificationStartedEvent(Event):
    """验证开始"""
    event_type: str = "verification_started"
    expectations_count: int = 0


@dataclass
class VerificationCompletedEvent(Event):
    """验证完成"""
    event_type: str = "verification_completed"
    passed: bool = False
    passed_count: int = 0
    failed_count: int = 0


# === 补救事件 ===

@dataclass
class RemediationTriggeredEvent(Event):
    """补救触发"""
    event_type: str = "remediation_triggered"
    failure_code: str = ""
    remediation_strategy: str = ""
    attempt_number: int = 0


# === 批次密封事件 ===

@dataclass
class BatchSealedEvent(Event):
    """批次密封（用于审计）"""
    event_type: str = "batch_sealed"
    batch_id: str = ""
    merkle_root: str = ""
    signature: str = ""
    sealed_event_ids: list = field(default_factory=list)
    event_count: int = 0
```

---

## 三、初始化顺序（Startup Sequence）

### 3.1 初始化契约

```python
# core/bootstrap.py

from dataclasses import dataclass
from typing import Optional
import yaml


@dataclass
class BootstrapResult:
    """启动结果"""
    success: bool
    agent_runtime: Optional['AgentRuntime'] = None
    error: Optional[str] = None


class AgentBootstrap:
    """
    Agent 启动器
    严格按顺序初始化，任何一步失败都终止
    """
    
    def bootstrap(self, config_path: str) -> BootstrapResult:
        """
        启动顺序（不可改变）：
        1. ConfigLoader → 加载配置
        2. EventLog → 初始化事件日志（后续所有组件都依赖它）
        3. PolicyEngine → 加载策略
        4. ToolRegistry → 注册工具
        5. ModelAdapter → 初始化模型适配器
        6. ToolRuntime → 初始化工具执行运行时
        7. ContextAssembler → 初始化上下文装配器
        8. Validators → 初始化验证器
        9. AgentRuntime → 组装并返回
        """
        try:
            # Step 1: 加载配置
            config = self._load_config(config_path)
            
            # Step 2: 初始化事件日志（最先，其他组件都要写日志）
            event_log = self._init_event_log(config)
            
            # Step 3: 初始化策略引擎
            policy_engine = self._init_policy_engine(config, event_log)
            
            # Step 4: 初始化工具注册表
            tool_registry = self._init_tool_registry(config, event_log)
            
            # Step 5: 初始化模型适配器
            model_adapter = self._init_model_adapter(config, event_log)
            
            # Step 6: 初始化工具运行时
            tool_runtime = self._init_tool_runtime(
                tool_registry, policy_engine, event_log
            )
            
            # Step 7: 初始化上下文装配器
            context_assembler = self._init_context_assembler(config, event_log)
            
            # Step 8: 初始化验证器
            validators = self._init_validators(tool_registry, policy_engine)
            
            # Step 9: 组装 AgentRuntime
            agent_runtime = AgentRuntime(
                config=config,
                event_log=event_log,
                policy_engine=policy_engine,
                tool_registry=tool_registry,
                model_adapter=model_adapter,
                tool_runtime=tool_runtime,
                context_assembler=context_assembler,
                validators=validators,
            )
            
            # 记录启动成功
            event_log.append(RunStartedEvent(
                event_id=generate_id(),
                run_id="bootstrap",
                agent_id=config.agent_id,
                config_hash=hash_config(config),
            ))
            
            return BootstrapResult(success=True, agent_runtime=agent_runtime)
            
        except Exception as e:
            return BootstrapResult(success=False, error=str(e))
    
    def _load_config(self, config_path: str) -> 'AgentConfig':
        """加载配置"""
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        return AgentConfig(**raw)
    
    def _init_event_log(self, config: 'AgentConfig') -> 'EventLog':
        """初始化事件日志"""
        # MVP: 先用本地 append-only JSONL
        # 后续可替换为 WORM 存储
        return EventLog(
            storage_path=config.event_log_path,
            enable_hash_chain=True,
        )
    
    def _init_policy_engine(self, config: 'AgentConfig', event_log: 'EventLog') -> 'PolicyEngine':
        """初始化策略引擎"""
        return PolicyEngine(
            policy_config=config.policy_config,
            event_log=event_log,
        )
    
    def _init_tool_registry(self, config: 'AgentConfig', event_log: 'EventLog') -> 'ToolRegistry':
        """初始化工具注册表"""
        registry = ToolRegistry(event_log=event_log)
        
        # 加载工具契约
        for tool_config in config.tools:
            contract = ToolContract(**tool_config)
            registry.register(contract)
        
        return registry
    
    def _init_model_adapter(self, config: 'AgentConfig', event_log: 'EventLog') -> 'ModelAdapter':
        """初始化模型适配器"""
        return ModelAdapter(
            models_config=config.models,
            event_log=event_log,
        )
    
    def _init_tool_runtime(
        self,
        tool_registry: 'ToolRegistry',
        policy_engine: 'PolicyEngine',
        event_log: 'EventLog'
    ) -> 'ToolRuntime':
        """初始化工具运行时"""
        return ToolRuntime(
            registry=tool_registry,
            policy_engine=policy_engine,
            event_log=event_log,
        )
    
    def _init_context_assembler(self, config: 'AgentConfig', event_log: 'EventLog') -> 'ContextAssembler':
        """初始化上下文装配器"""
        return ContextAssembler(
            budget=config.context_budget,
            event_log=event_log,
        )
    
    def _init_validators(
        self,
        tool_registry: 'ToolRegistry',
        policy_engine: 'PolicyEngine'
    ) -> 'Validators':
        """初始化验证器集合"""
        return Validators(
            trust_boundary=TrustBoundaryValidator(tool_registry),
            coverage=DeterministicCoverageValidator(tool_registry),
            input_sanitizer=InputSanitizer(policy_engine),
        )
```

### 3.2 配置文件示例

```yaml
# config/agent_config.yaml

agent_id: "coding-agent-001"
version: "1.0.0"

# 模型配置
models:
  default: "claude-sonnet"
  fallback: "gpt-4o-mini"
  planning: "claude-sonnet"
  execution: "claude-haiku"

# 上下文预算
context_budget:
  max_tokens: 100000
  skills_budget: 20000
  history_budget: 30000
  docs_budget: 20000

# 事件日志
event_log_path: "/var/log/agent/events.jsonl"

# 策略配置
policy_config:
  approval_required_for:
    - "NON_IDEMPOTENT_EFFECT"
    - "COMPENSATABLE"
  max_remediations: 3
  
# 工具配置
tools:
  - name: "read_file"
    risk_level: "READ_ONLY"
    timeout_seconds: 30
    produces_assertions:
      - type: "file_content"
        produces: {}
    
  - name: "write_file"
    risk_level: "IDEMPOTENT_WRITE"
    timeout_seconds: 60
    requires_approval: false
    produces_assertions:
      - type: "file_modified"
        produces: {}
    
  - name: "run_tests"
    risk_level: "READ_ONLY"
    timeout_seconds: 300
    produces_assertions:
      - type: "test_pass"
        produces: { "suite": "unit" }
      - type: "evidence_type"
        produces: { "types": ["TEST_REPORT"] }
    
  - name: "execute_command"
    risk_level: "NON_IDEMPOTENT_EFFECT"
    timeout_seconds: 120
    requires_approval: true
    rollback_capable: false
```

---

## 四、Runtime Loop（运行主循环）

### 4.1 六步编排

```python
# core/dare_utils.py

from typing import Optional
from enum import Enum


class AgentRuntime:
    """
    Agent 运行时
    主循环：Observe → Plan → Validate → Execute → Verify → Remediate
    """
    
    def __init__(
        self,
        config: 'AgentConfig',
        event_log: 'EventLog',
        policy_engine: 'PolicyEngine',
        tool_registry: 'ToolRegistry',
        model_adapter: 'ModelAdapter',
        tool_runtime: 'ToolRuntime',
        context_assembler: 'ContextAssembler',
        validators: 'Validators',
    ):
        self.config = config
        self.event_log = event_log
        self.policy_engine = policy_engine
        self.tool_registry = tool_registry
        self.model_adapter = model_adapter
        self.tool_runtime = tool_runtime
        self.context_assembler = context_assembler
        self.validators = validators
    
    async def run(self, task: Task) -> RunResult:
        """
        执行任务
        严格按六步执行，每步都写事件日志
        """
        # 初始化运行状态
        state = RunState(
            run_id=generate_id(),
            task=task,
            phase=RunPhase.INITIALIZING,
        )
        
        # 记录任务接收
        await self._log_event(TaskReceivedEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            task_id=task.task_id,
            task_description=task.description,
            expectations_count=len(task.expectations),
        ))
        
        try:
            while state.phase != RunPhase.COMPLETED and state.phase != RunPhase.FAILED:
                state = await self._execute_phase(state)
            
            return self._build_result(state)
            
        except Exception as e:
            state.phase = RunPhase.FAILED
            await self._log_error(state, e)
            return self._build_result(state, error=e)
    
    async def _execute_phase(self, state: RunState) -> RunState:
        """执行当前阶段"""
        
        if state.phase == RunPhase.INITIALIZING:
            return await self._phase_observe(state)
        
        elif state.phase == RunPhase.OBSERVING:
            return await self._phase_plan(state)
        
        elif state.phase == RunPhase.PLANNING:
            return await self._phase_validate(state)
        
        elif state.phase == RunPhase.VALIDATING:
            return await self._phase_execute(state)
        
        elif state.phase == RunPhase.EXECUTING:
            return await self._phase_verify(state)
        
        elif state.phase == RunPhase.VERIFYING:
            return await self._phase_remediate_or_complete(state)
        
        elif state.phase == RunPhase.REMEDIATING:
            return await self._phase_plan(state)  # 回到规划
        
        return state
    
    # === 六步实现 ===
    
    async def _phase_observe(self, state: RunState) -> RunState:
        """
        Step 1: Observe
        收集任务输入 + 当前状态快照
        """
        state.phase = RunPhase.OBSERVING
        
        # 装配上下文
        context = await self.context_assembler.assemble(
            task=state.task,
            run_state=state,
        )
        
        # 存入状态
        state.assembled_context = context
        
        # 进入规划
        state.phase = RunPhase.PLANNING
        return state
    
    async def _phase_plan(self, state: RunState) -> RunState:
        """
        Step 2: Plan
        LLM 产出计划（不可信）
        """
        # 调用模型生成计划
        plan = await self.model_adapter.generate_plan(
            task=state.task,
            context=state.assembled_context,
            previous_failures=self._get_previous_failures(state),
        )
        
        state.current_plan = plan
        
        # 记录计划（记录但不信任）
        await self._log_event(PlanProposedEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            plan_id=plan.plan_id,
            plan_hash=hash_plan(plan),
            model_used=plan.created_by,
        ))
        
        state.phase = RunPhase.VALIDATING
        return state
    
    async def _phase_validate(self, state: RunState) -> RunState:
        """
        Step 3: Validate
        验证计划：TrustBoundary + Coverage + Policy
        这一步决定"能不能进执行"
        """
        plan = state.current_plan
        errors = []
        
        # 3.1 TrustBoundary：派生可信字段
        validated_steps = []
        for step in plan.steps:
            try:
                validated = self.validators.trust_boundary.derive(step)
                validated_steps.append(validated)
            except ValidationError as e:
                errors.append(e)
        
        # 3.2 InputSanitizer：消毒输入
        for validated_step in validated_steps:
            try:
                sanitized_input = self.validators.input_sanitizer.sanitize(
                    validated_step.tool,
                    validated_step.tool_input,
                )
                validated_step.tool_input = sanitized_input
            except SanitizationError as e:
                errors.append(e)
        
        # 3.3 DeterministicCoverage：检查覆盖
        coverage_result = self.validators.coverage.validate(
            expectations=state.task.expectations,
            steps=validated_steps,
        )
        if not coverage_result.valid:
            errors.extend(coverage_result.errors)
        
        # 3.4 PolicyEngine：检查策略
        for validated_step in validated_steps:
            policy_result = self.policy_engine.check_tool(
                tool=validated_step.tool,
                risk_level=validated_step.risk_level,
                context=state,
            )
            if not policy_result.allowed:
                errors.append(PolicyError(policy_result.reason))
        
        # 判断是否通过
        if errors:
            await self._log_event(PlanRejectedEvent(
                event_id=generate_id(),
                run_id=state.run_id,
                plan_id=plan.plan_id,
                rejection_reasons=[str(e) for e in errors],
            ))
            
            # 检查是否还能重试
            if state.remediation_count < state.max_remediations:
                state.phase = RunPhase.REMEDIATING
                state.remediation_count += 1
            else:
                state.phase = RunPhase.FAILED
            
            return state
        
        # 验证通过
        state.validated_steps = validated_steps
        
        await self._log_event(PlanValidatedEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            plan_id=plan.plan_id,
            validated_steps_count=len(validated_steps),
        ))
        
        state.phase = RunPhase.EXECUTING
        return state
    
    async def _phase_execute(self, state: RunState) -> RunState:
        """
        Step 4: Execute
        按步骤执行（所有工具调用走 ToolRuntime）
        """
        for i, step in enumerate(state.validated_steps):
            state.current_step_index = i
            
            # 记录步骤开始
            await self._log_event(StepStartedEvent(
                event_id=generate_id(),
                run_id=state.run_id,
                step_id=step.step_id,
                tool=step.tool,
                input_hash=hash_dict(step.tool_input),
            ))
            
            # 执行工具（强制走 ToolRuntime）
            result = await self.tool_runtime.invoke(
                tool_name=step.tool,
                input=step.tool_input,
                context=ExecutionContext(
                    run_id=state.run_id,
                    step_id=step.step_id,
                    risk_level=step.risk_level,
                    requires_approval=step.requires_approval,
                ),
            )
            
            # 记录结果
            step_result = StepResult(
                step_id=step.step_id,
                success=result.success,
                output=result.output,
                evidence_ref=result.evidence_ref,
                error=result.error,
            )
            state.step_results.append(step_result)
            
            if result.evidence_ref:
                state.evidence_refs.append(result.evidence_ref)
            
            # 记录事件
            if result.success:
                await self._log_event(StepCompletedEvent(
                    event_id=generate_id(),
                    run_id=state.run_id,
                    step_id=step.step_id,
                    success=True,
                    evidence_ref=result.evidence_ref,
                ))
            else:
                await self._log_event(StepFailedEvent(
                    event_id=generate_id(),
                    run_id=state.run_id,
                    step_id=step.step_id,
                    failure_code=result.error.code,
                    failure_category=result.error.category,
                ))
                
                # 失败处理
                if result.error.category == "permanent":
                    state.phase = RunPhase.FAILED
                    return state
                elif result.error.category in ["transient", "needs_approval"]:
                    state.phase = RunPhase.REMEDIATING
                    return state
        
        # 所有步骤执行完成
        state.phase = RunPhase.VERIFYING
        return state
    
    async def _phase_verify(self, state: RunState) -> RunState:
        """
        Step 5: Verify
        按 Expectation.verification_spec 执行验收（不靠模型）
        """
        await self._log_event(VerificationStartedEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            expectations_count=len(state.task.expectations),
        ))
        
        verification_results = []
        
        for exp in state.task.expectations:
            # 根据 verification_spec 执行验证
            result = await self._verify_expectation(exp, state)
            verification_results.append(result)
        
        # 生成验证报告
        passed = all(r.passed for r in verification_results if r.required)
        
        state.verification_report = VerificationReport(
            passed=passed,
            results=verification_results,
        )
        
        await self._log_event(VerificationCompletedEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            passed=passed,
            passed_count=sum(1 for r in verification_results if r.passed),
            failed_count=sum(1 for r in verification_results if not r.passed),
        ))
        
        return state
    
    async def _phase_remediate_or_complete(self, state: RunState) -> RunState:
        """
        Step 6: Remediate or Complete
        验证通过则完成，否则触发补救
        """
        if state.verification_report and state.verification_report.passed:
            state.phase = RunPhase.COMPLETED
            state.finished_at = datetime.now()
            
            await self._log_event(RunCompletedEvent(
                event_id=generate_id(),
                run_id=state.run_id,
                success=True,
                verification_passed=True,
                evidence_refs=state.evidence_refs,
            ))
            
            return state
        
        # 验证失败，检查是否还能补救
        if state.remediation_count >= state.max_remediations:
            state.phase = RunPhase.FAILED
            state.finished_at = datetime.now()
            
            await self._log_event(RunCompletedEvent(
                event_id=generate_id(),
                run_id=state.run_id,
                success=False,
                verification_passed=False,
                evidence_refs=state.evidence_refs,
            ))
            
            return state
        
        # 触发补救
        state.remediation_count += 1
        
        await self._log_event(RemediationTriggeredEvent(
            event_id=generate_id(),
            run_id=state.run_id,
            failure_code=self._get_primary_failure_code(state),
            remediation_strategy="replan",
            attempt_number=state.remediation_count,
        ))
        
        state.phase = RunPhase.REMEDIATING
        return state
```

---

## 五、核心组件接口

### 5.1 七个不可变接口

```python
# components/interfaces.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class IModelAdapter(ABC):
    """模型适配器接口"""
    
    @abstractmethod
    async def generate_plan(
        self,
        task: Task,
        context: 'AssembledContext',
        previous_failures: List[FailureInfo],
    ) -> Plan:
        """生成计划"""
        pass
    
    @abstractmethod
    async def generate_patch(
        self,
        state: RunState,
        failure: FailureInfo,
    ) -> 'PlanPatch':
        """生成修补计划"""
        pass


class IToolRegistry(ABC):
    """工具注册表接口"""
    
    @abstractmethod
    def register(self, contract: 'ToolContract') -> None:
        """注册工具"""
        pass
    
    @abstractmethod
    def get(self, tool_name: str) -> Optional['ToolContract']:
        """获取工具契约"""
        pass
    
    @abstractmethod
    def list(self) -> List['ToolSummary']:
        """列出所有工具摘要"""
        pass


class IToolRuntime(ABC):
    """工具运行时接口"""
    
    @abstractmethod
    async def invoke(
        self,
        tool_name: str,
        input: Dict[str, Any],
        context: 'ExecutionContext',
    ) -> 'ToolResult':
        """
        调用工具
        这是唯一的工具调用入口
        强制：policy check + audit + evidence
        """
        pass


class IPolicyEngine(ABC):
    """策略引擎接口"""
    
    @abstractmethod
    def check_tool(
        self,
        tool: str,
        risk_level: 'RiskLevel',
        context: 'RunState',
    ) -> 'PolicyResult':
        """检查工具调用策略"""
        pass
    
    @abstractmethod
    def check_egress(
        self,
        destination: str,
        data_classification: str,
        context: 'ExecutionContext',
    ) -> 'PolicyResult':
        """检查出站策略"""
        pass


class IEventLog(ABC):
    """事件日志接口"""
    
    @abstractmethod
    async def append(self, event: Event) -> None:
        """追加事件（唯一写入方式）"""
        pass
    
    @abstractmethod
    async def get(self, event_id: str) -> Optional[Event]:
        """获取事件"""
        pass
    
    @abstractmethod
    async def export(self, run_id: str) -> List[Event]:
        """导出运行的所有事件"""
        pass


class IContextAssembler(ABC):
    """上下文装配器接口"""
    
    @abstractmethod
    async def assemble(
        self,
        task: Task,
        run_state: RunState,
    ) -> 'AssembledContext':
        """装配上下文"""
        pass


class IVerifier(ABC):
    """验证器接口"""
    
    @abstractmethod
    async def verify(
        self,
        expectation: Expectation,
        evidence_refs: List[str],
        context: 'VerificationContext',
    ) -> 'VerificationResult':
        """执行验证"""
        pass
```

### 5.2 工具契约

```python
# components/tool_registry.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class RiskLevel(Enum):
    """工具风险级别"""
    READ_ONLY = 1
    IDEMPOTENT_WRITE = 2
    NON_IDEMPOTENT_EFFECT = 3
    COMPENSATABLE = 4


@dataclass
class Assertion:
    """断言（工具产出）"""
    type: str
    produces: Dict[str, Any]


@dataclass
class ToolContract:
    """
    工具契约
    这是工具的"真相源"，所有安全关键字段从这里派生
    """
    # 基本信息
    name: str
    description: str
    version: str = "1.0.0"
    
    # 风险与权限（框架强制，不允许 LLM 修改）
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    requires_approval: bool = False
    rollback_capable: bool = False
    
    # Schema
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 产出断言（用于确定性覆盖计算）
    produces_assertions: List[Assertion] = field(default_factory=list)
    
    # 执行参数
    timeout_seconds: int = 30
    max_retries: int = 0  # 非幂等工具必须为0
    
    # 执行函数
    execute_fn: Optional[Callable] = None
    compensate_fn: Optional[Callable] = None


class ToolRegistry(IToolRegistry):
    """工具注册表"""
    
    def __init__(self, event_log: IEventLog):
        self._tools: Dict[str, ToolContract] = {}
        self._event_log = event_log
    
    def register(self, contract: ToolContract) -> None:
        """注册工具"""
        # 契约校验
        self._validate_contract(contract)
        
        self._tools[contract.name] = contract
    
    def get(self, tool_name: str) -> Optional[ToolContract]:
        """获取工具契约"""
        return self._tools.get(tool_name)
    
    def list(self) -> List['ToolSummary']:
        """列出所有工具摘要"""
        return [
            ToolSummary(
                name=t.name,
                description=t.description,
                risk_level=t.risk_level,
            )
            for t in self._tools.values()
        ]
    
    def _validate_contract(self, contract: ToolContract) -> None:
        """校验契约一致性"""
        # 非幂等工具不能自动重试
        if contract.risk_level == RiskLevel.NON_IDEMPOTENT_EFFECT:
            if contract.max_retries > 0:
                raise ContractError("NON_IDEMPOTENT tools cannot have auto-retry")
        
        # 可补偿工具必须有补偿函数
        if contract.risk_level == RiskLevel.COMPENSATABLE:
            if not contract.compensate_fn:
                raise ContractError("COMPENSATABLE tools must have compensate_fn")
```

### 5.3 工具运行时

```python
# components/tool_runtime.py

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    evidence_ref: Optional[str] = None
    error: Optional[FailureInfo] = None


@dataclass
class ExecutionContext:
    """执行上下文"""
    run_id: str
    step_id: str
    risk_level: RiskLevel
    requires_approval: bool


class ToolRuntime(IToolRuntime):
    """
    工具运行时
    这是唯一的工具调用入口
    强制：policy check + audit + evidence
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: IPolicyEngine,
        event_log: IEventLog,
        evidence_factory: 'EvidenceFactory' = None,
    ):
        self._registry = registry
        self._policy_engine = policy_engine
        self._event_log = event_log
        self._evidence_factory = evidence_factory or EvidenceFactory(event_log)
    
    async def invoke(
        self,
        tool_name: str,
        input: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """
        调用工具
        所有工具调用必须经过这里
        """
        # 1. 获取工具契约
        contract = self._registry.get(tool_name)
        if not contract:
            return ToolResult(
                success=False,
                output=None,
                error=FailureInfo(
                    code="E_TOOL_NOT_FOUND",
                    message=f"Tool {tool_name} not found",
                    category="permanent",
                    retryable=False,
                ),
            )
        
        # 2. 策略检查
        policy_result = self._policy_engine.check_tool(
            tool=tool_name,
            risk_level=contract.risk_level,
            context=context,
        )
        if not policy_result.allowed:
            return ToolResult(
                success=False,
                output=None,
                error=FailureInfo(
                    code="E_POLICY_DENIED",
                    message=policy_result.reason,
                    category="policy_denied",
                    retryable=False,
                ),
            )
        
        # 3. 审批检查（如果需要）
        if contract.requires_approval:
            approval = await self._check_approval(context)
            if not approval.approved:
                return ToolResult(
                    success=False,
                    output=None,
                    error=FailureInfo(
                        code="E_APPROVAL_REQUIRED",
                        message="Approval required",
                        category="needs_approval",
                        retryable=True,
                    ),
                )
        
        # 4. 记录调用事件
        await self._event_log.append(ToolInvokedEvent(
            event_id=generate_id(),
            run_id=context.run_id,
            step_id=context.step_id,
            tool=tool_name,
            risk_level=contract.risk_level.name,
        ))
        
        # 5. 执行工具
        try:
            output = await self._execute(contract, input, context)
            
            # 6. 生成证据
            evidence_ref = await self._evidence_factory.create(
                source="tool_runtime",
                content={"tool": tool_name, "output_hash": hash_any(output)},
                context=context,
            )
            
            return ToolResult(
                success=True,
                output=output,
                evidence_ref=evidence_ref,
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=FailureInfo(
                    code="E_TOOL_EXECUTION_ERROR",
                    message=str(e),
                    category="transient" if self._is_transient(e) else "permanent",
                    retryable=self._is_transient(e),
                ),
            )
    
    async def _execute(
        self,
        contract: ToolContract,
        input: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """执行工具"""
        if contract.execute_fn:
            return await contract.execute_fn(input, context)
        raise NotImplementedError(f"Tool {contract.name} has no execute_fn")
```

---

## 六、信任边界验证

```python
# validators/trust_boundary.py


class TrustBoundaryValidator:
    """
    信任边界验证器
    关键：安全关键字段从 Registry 派生，不信任 LLM
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self._registry = tool_registry
    
    def derive(self, plan_step: PlanStep) -> ValidatedStep:
        """
        从 PlanStep（不可信）派生 ValidatedStep（可信）
        所有安全关键字段从 ToolRegistry 读取
        """
        # 获取工具契约
        contract = self._registry.get(plan_step.tool)
        if not contract:
            raise ValidationError(f"Unknown tool: {plan_step.tool}")
        
        # 派生可信字段（覆盖 LLM 填写的）
        return ValidatedStep(
            step_id=plan_step.step_id,
            order=plan_step.order,
            description=plan_step.description,
            tool=plan_step.tool,
            tool_input=plan_step.tool_input,  # 后续由 InputSanitizer 消毒
            
            # 以下字段全部从 Registry 派生，不用 LLM 填的
            risk_level=contract.risk_level,
            requires_approval=contract.requires_approval,
            rollback_capable=contract.rollback_capable,
            produces_assertions=contract.produces_assertions,
            
            trust_level=TrustLevel.SYSTEM,  # 系统派生，可信
        )
```

---

## 七、确定性覆盖验证

```python
# validators/coverage_validator.py


class DeterministicCoverageValidator:
    """
    确定性覆盖验证器
    覆盖关系是集合运算：requires ⊆ produces
    不涉及语义理解，不需要模型参与
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self._registry = tool_registry
    
    def validate(
        self,
        expectations: List[Expectation],
        steps: List[ValidatedStep],
    ) -> CoverageValidationResult:
        """验证覆盖关系"""
        errors = []
        coverage_map = {}
        
        for exp in expectations:
            if exp.priority != "MUST":
                continue
            
            # 检查 spec 是否存在
            if not exp.verification_spec:
                errors.append(ValidationError(
                    code="E_NO_VERIFICATION_SPEC",
                    message=f"Expectation {exp.expectation_id} has no verification_spec",
                ))
                continue
            
            # 确定性查找覆盖步骤
            covering_steps = self._find_covering_steps(exp.verification_spec, steps)
            
            if not covering_steps:
                errors.append(ValidationError(
                    code="E_EXPECTATION_NOT_COVERED",
                    message=f"MUST expectation not covered: {exp.expectation_id}",
                ))
            else:
                coverage_map[exp.expectation_id] = covering_steps
        
        return CoverageValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            coverage_map=coverage_map,
        )
    
    def _find_covering_steps(
        self,
        spec: VerificationSpec,
        steps: List[ValidatedStep],
    ) -> List[str]:
        """
        确定性查找覆盖步骤
        纯集合运算
        """
        covering = []
        
        for step in steps:
            for assertion in step.produces_assertions:
                if self._assertion_satisfies_spec(assertion, spec):
                    covering.append(step.step_id)
                    break
        
        return covering
    
    def _assertion_satisfies_spec(self, assertion: Assertion, spec: VerificationSpec) -> bool:
        """判断断言是否满足规格"""
        if assertion.type != spec.type:
            return False
        
        # 根据类型做具体匹配
        if spec.type == "test_pass":
            return assertion.produces.get("suite") == spec.config.get("suite")
        
        elif spec.type == "evidence_type":
            required = set(spec.config.get("required", []))
            produced = set(assertion.produces.get("types", []))
            return required <= produced
        
        return False
```

---

## 八、MVP 实施计划

### 8.1 三阶段落地

```
阶段 1：骨架跑通（1-2周）
─────────────────────────
目标：主循环能跑，能执行简单任务

必须完成：
- [ ] 数据结构定义（Task/Plan/Step/RunState）
- [ ] EventLog（本地 append-only JSONL）
- [ ] ModelAdapter（接一个模型）
- [ ] AgentRuntime 六步编排
- [ ] ToolRegistry + 2-3 个简单工具
- [ ] 简化版 ToolRuntime（无审批）

验收标准：
- 能接收任务，生成计划，执行工具，输出结果
- 所有步骤都有事件日志


阶段 2：门禁落地（2-3周）
─────────────────────────
目标：核心安全机制生效

必须完成：
- [ ] TrustBoundaryValidator（派生可信字段）
- [ ] DeterministicCoverageValidator
- [ ] InputSanitizer
- [ ] PolicyEngine（工具权限检查）
- [ ] 完整的 ToolRuntime（含审批）
- [ ] EvidenceFactory

验收标准：
- LLM 填的 risk_level 被忽略，只用 Registry 的
- 不符合覆盖要求的 Plan 被拒绝
- 高风险工具调用有审批


阶段 3：安全增强（3-4周）
─────────────────────────
目标：闭环可验证

可以完成：
- [ ] Hash Chain（EventLog 防篡改）
- [ ] Context 注入隔离
- [ ] Sandbox（代码执行隔离）
- [ ] TokenStore（数据令牌化）
- [ ] 外部 Verifier 脚本

验收标准：
- EventLog 可独立验签
- 沙箱内代码无法访问网络
```

### 8.2 MVP 最小集合（6件事）

```
1. ToolRegistry + TrustBoundary
   → risk_level/approval/permissions 全从可信源派生

2. ToolRuntime 门禁
   → 所有工具调用走这里，强制 policy + audit

3. DeterministicCoverageValidator
   → requires ⊆ produces，不靠模型

4. EventLog (append-only + hash chain)
   → 本地 JSONL 先行，接口定死

5. 六步编排主循环
   → Observe→Plan→Validate→Execute→Verify→Remediate

6. 配置化启动
   → Bootstrap 顺序固定，失败快速退出
```

---

## 九、GPT 提醒的补充点

### 9.1 并发/重试/幂等策略

```python
# 框架级规定

class RetryPolicy:
    """重试策略 - 由框架强制"""
    
    # 谁负责重试？
    # → ToolRuntime 负责，不是 StepExecutor
    
    # 什么情况重试？
    # → 只有 ToolContract.max_retries > 0 且 error.retryable=True
    
    # 幂等如何保证？
    # → 由 ToolContract 声明，执行器必须遵守
    # → 非幂等工具 max_retries 必须为 0
    
    @staticmethod
    def should_retry(contract: ToolContract, error: FailureInfo, attempt: int) -> bool:
        if not error.retryable:
            return False
        if attempt >= contract.max_retries:
            return False
        if contract.risk_level == RiskLevel.NON_IDEMPOTENT_EFFECT:
            return False  # 非幂等永不重试
        return True
```

### 9.2 ModelAdapter 的重要性

```python
# components/model_adapter.py

class ModelAdapter(IModelAdapter):
    """
    模型适配器
    GPT 提醒：这是最容易被忽略、但上线最容易爆炸的点
    """
    
    def __init__(self, models_config: Dict, event_log: IEventLog):
        self._models = {}
        self._event_log = event_log
        
        # 初始化各模型的适配器
        for name, config in models_config.items():
            self._models[name] = self._create_adapter(config)
    
    async def generate_plan(
        self,
        task: Task,
        context: 'AssembledContext',
        previous_failures: List[FailureInfo],
    ) -> Plan:
        """生成计划"""
        model = self._select_model("planning")
        
        # 构造 prompt
        prompt = self._build_plan_prompt(task, context, previous_failures)
        
        # 调用模型
        response = await model.generate(prompt)
        
        # 解析响应（这里是最容易出问题的地方）
        plan = self._parse_plan_response(response, task)
        
        return plan
    
    def _parse_plan_response(self, response: str, task: Task) -> Plan:
        """
        解析模型响应
        关键：处理各种格式差异、JSON 不稳定等问题
        """
        # 尝试多种解析方式
        try:
            # 方式1：直接 JSON
            return self._parse_json(response)
        except:
            pass
        
        try:
            # 方式2：从 markdown code block 提取
            return self._parse_markdown_json(response)
        except:
            pass
        
        try:
            # 方式3：结构化提取
            return self._structured_extract(response, task)
        except:
            pass
        
        raise PlanParseError(f"Cannot parse plan from response")
```

---

## 十、总结

### 这份文档回答了什么

1. **目录结构**：框架代码怎么组织
2. **数据结构**：状态模型是什么、哪些可信哪些不可信
3. **启动顺序**：初始化的契约是什么
4. **运行流程**：六步编排怎么执行
5. **核心接口**：7个不可变接口是什么
6. **实施计划**：MVP 怎么分阶段落地

### 与 v2.0-v2.4 的关系

```
v2.0-v2.4：理念、闭环、安全机制
本文档：  把这些东西落地成可编码的框架骨架

v2.4 的闭环 → 本文档的验证器
v2.4 的信任边界 → 本文档的 TrustBoundaryValidator
v2.4 的确定性覆盖 → 本文档的 DeterministicCoverageValidator
v2.4 的事件日志 → 本文档的 EventLog 接口
```

### 下一步

1. 把这份文档变成代码目录
2. 先实现阶段1（骨架跑通）
3. 再逐步添加阶段2/3的功能

---

*文档状态：框架骨架设计，可开始编码*
