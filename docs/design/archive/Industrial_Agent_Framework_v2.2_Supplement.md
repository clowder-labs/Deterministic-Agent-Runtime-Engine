# 工业级 Agent 框架设计文档 v2.2 补充章节

> 本文档回答评审会问爆的6个硬问题，并明确LangGraph的架构定位。

---

## 前置：LangGraph 在本架构中的定位

### 定位：可选的编排层实现，不是架构核心

```
┌─────────────────────────────────────────────────────────────────────┐
│                        架构分层                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 4: 应用层        [业务Agent]                                 │
│                              │                                      │
│  Layer 3: 编排层        [LangGraph StateGraph] ← 可替换             │
│                              │                                      │
│  Layer 2: 核心运行时    [Tool Runtime / Validator / Egress] ← 自研  │
│                              │                                      │
│  Layer 1: 基础设施      [Event Log / Policy Engine] ← 自研          │
│                              │                                      │
│  Layer 0: 存储/网络     [PostgreSQL / Redis / LiteLLM]              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

关键原则：
• Layer 2/1 必须自研（P0承重梁）
• Layer 3 可以用LangGraph，也可以自研
• Layer 2/1 的接口设计必须与 Layer 3 解耦
```

### LangGraph 的价值与边界

| LangGraph 提供 | 我们如何使用 | 边界 |
|---------------|-------------|------|
| StateGraph 编排 | 作为 PER Loop 的实现载体 | 不依赖其内部状态语义 |
| Checkpointer | 可作为 Event Log 的存储后端之一 | 但 Event Log 语义自己定义 |
| Time-travel | 用于调试和回放 | 生产回滚用自己的补偿栈 |
| Human-in-loop | 作为触发点 | 审批逻辑走自研 Approval Protocol |
| Tool binding | 不使用 | 工具必须走自研 Tool Runtime |

### 与LangGraph集成的接口设计

```python
# 核心原则：LangGraph只负责"流程编排"，不碰"状态语义"和"工具执行"

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

class AgentState(TypedDict):
    """LangGraph状态 - 只存流程控制信息"""
    task_id: str
    current_phase: str  # plan / execute / reflect / validate
    iteration: int
    # 注意：不存业务状态，业务状态在 Event Log 里

def create_agent_graph(
    tool_runtime: ToolRuntime,      # 自研
    done_validator: DoneValidator,  # 自研
    event_log: EventLog,            # 自研
    policy_engine: PolicyEngine,    # 自研
) -> StateGraph:
    """
    创建Agent图
    LangGraph只做流程编排，所有实际工作委托给自研组件
    """
    graph = StateGraph(AgentState)
    
    # Plan节点 - 调用自研组件
    async def plan_node(state: AgentState) -> AgentState:
        # 所有LLM调用必须走EgressGateway（自研组件强制）
        plan = await planner.generate_plan(state["task_id"])
        
        # Plan校验（自研组件）
        validation = await plan_validator.validate(plan)
        if not validation.approved:
            raise PlanRejected(validation.reason)
        
        # 写入Event Log（自研组件）
        await event_log.append(PlanCreatedEvent(plan))
        
        return {**state, "current_phase": "execute"}
    
    # Execute节点 - 工具执行必须走ToolRuntime
    async def execute_node(state: AgentState) -> AgentState:
        plan = await event_log.get_current_plan(state["task_id"])
        
        for step in plan.steps:
            # 所有工具调用必须走ToolRuntime（不允许直接调用）
            result = await tool_runtime.execute(step.tool, step.input)
            await event_log.append(StepExecutedEvent(step, result))
        
        return {**state, "current_phase": "validate"}
    
    # Validate节点 - 使用自研DoneValidator
    async def validate_node(state: AgentState) -> AgentState:
        result = await done_validator.validate(state["task_id"])
        
        if result.status == DoneStatus.DONE:
            return {**state, "current_phase": "done"}
        elif result.status == DoneStatus.NOT_DONE:
            # 触发Remediation（不是无脑反思）
            return {**state, "current_phase": "remediate", "iteration": state["iteration"] + 1}
        else:  # INCONCLUSIVE
            # 走降级策略
            return await handle_inconclusive(state, result)
    
    # 构建图
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("validate", validate_node)
    graph.add_node("remediate", remediate_node)
    
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "validate")
    graph.add_conditional_edges("validate", route_after_validate)
    graph.add_edge("remediate", "plan")  # 修复后重新规划
    
    graph.set_entry_point("plan")
    
    return graph.compile(checkpointer=PostgresSaver(...))
```

---

## 补充章节 1：写操作回滚保证

> **评审问题**："你怎么保证写操作一定可回滚？没Git怎么办？"

### 1.1 WorkspaceSafetyGate（工作区安全门）

```python
class WorkspaceSafetyGate:
    """
    工作区安全门
    原则：任何写操作执行前，必须先创建回滚句柄
    """
    
    def __init__(self, event_log: EventLog, rollback_providers: List[RollbackProvider]):
        self.event_log = event_log
        self.rollback_providers = {p.name: p for p in rollback_providers}
    
    async def prepare_write(
        self, 
        tool: Tool, 
        input: dict,
        context: ExecutionContext
    ) -> WritePermit:
        """
        准备写操作
        返回WritePermit，包含回滚句柄
        没有回滚句柄 = 拒绝执行
        """
        if tool.risk_level == RiskLevel.READ_ONLY:
            return WritePermit(allowed=True, rollback_handle=None)
        
        # 选择回滚策略
        provider = self._select_rollback_provider(tool, input, context)
        
        # 创建回滚句柄
        try:
            rollback_handle = await provider.create_handle(tool, input)
        except RollbackNotPossible as e:
            # 无法创建回滚句柄
            if tool.risk_level >= RiskLevel.NON_IDEMPOTENT_EFFECT:
                # 高风险操作必须有回滚能力
                return WritePermit(
                    allowed=False, 
                    reason=f"Cannot create rollback handle: {e}"
                )
            else:
                # 中风险操作记录警告但允许
                await self.event_log.append(RollbackWarningEvent(tool, str(e)))
                return WritePermit(allowed=True, rollback_handle=None, warning=str(e))
        
        # 写入Event Log
        await self.event_log.append(RollbackHandleCreatedEvent(
            tool=tool.name,
            handle=rollback_handle,
            context=context
        ))
        
        return WritePermit(allowed=True, rollback_handle=rollback_handle)
    
    def _select_rollback_provider(self, tool: Tool, input: dict, context: ExecutionContext) -> RollbackProvider:
        """根据工具类型选择回滚提供者"""
        if tool.operates_on == "git_workspace":
            return self.rollback_providers["git"]
        elif tool.operates_on == "filesystem":
            return self.rollback_providers["snapshot"]
        elif tool.operates_on == "database":
            return self.rollback_providers["transaction"]
        else:
            return self.rollback_providers["generic"]


# 回滚提供者示例
class GitRollbackProvider(RollbackProvider):
    """Git回滚提供者"""
    name = "git"
    
    async def create_handle(self, tool: Tool, input: dict) -> RollbackHandle:
        """执行前创建commit"""
        # 暂存当前更改
        await self.git.add(".")
        commit_hash = await self.git.commit(
            message=f"[agent-checkpoint] Before {tool.name}",
            allow_empty=True
        )
        
        return GitRollbackHandle(
            commit_hash=commit_hash,
            branch=await self.git.current_branch(),
            created_at=now()
        )
    
    async def rollback(self, handle: GitRollbackHandle) -> RollbackResult:
        """回滚到checkpoint"""
        await self.git.reset("--hard", handle.commit_hash)
        return RollbackResult(success=True, rolled_back_to=handle.commit_hash)


class SnapshotRollbackProvider(RollbackProvider):
    """文件系统快照回滚提供者（无Git时使用）"""
    name = "snapshot"
    
    async def create_handle(self, tool: Tool, input: dict) -> RollbackHandle:
        """创建文件快照"""
        affected_paths = self._predict_affected_paths(tool, input)
        
        snapshot_id = generate_id()
        snapshot_dir = f"/tmp/agent_snapshots/{snapshot_id}"
        
        for path in affected_paths:
            if os.path.exists(path):
                # 复制原文件
                dest = os.path.join(snapshot_dir, path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(path, dest)
        
        return SnapshotRollbackHandle(
            snapshot_id=snapshot_id,
            snapshot_dir=snapshot_dir,
            affected_paths=affected_paths,
            created_at=now()
        )
    
    async def rollback(self, handle: SnapshotRollbackHandle) -> RollbackResult:
        """从快照恢复"""
        for path in handle.affected_paths:
            snapshot_path = os.path.join(handle.snapshot_dir, path)
            if os.path.exists(snapshot_path):
                shutil.copy2(snapshot_path, path)
            else:
                # 原本不存在的文件，删除
                if os.path.exists(path):
                    os.remove(path)
        
        return RollbackResult(success=True)
```

### 1.2 Compensation Stack（补偿栈）

```python
class CompensationStack:
    """
    补偿栈 - Saga模式的逆序撤回
    原则：写入Event Log，可重启恢复
    """
    
    def __init__(self, event_log: EventLog):
        self.event_log = event_log
    
    async def push(self, task_id: str, compensation: Compensation):
        """压入补偿操作"""
        await self.event_log.append(CompensationPushedEvent(
            task_id=task_id,
            compensation=compensation,
            stack_index=await self._get_stack_size(task_id)
        ))
    
    async def rollback_all(self, task_id: str) -> RollbackReport:
        """
        执行全部补偿（逆序）
        这是Saga的核心：每个成功的操作都有对应的补偿操作
        """
        compensations = await self._get_stack(task_id)
        results = []
        
        # 逆序执行补偿
        for comp in reversed(compensations):
            try:
                result = await self._execute_compensation(comp)
                results.append(CompensationResult(
                    compensation=comp,
                    success=True,
                    result=result
                ))
                await self.event_log.append(CompensationExecutedEvent(comp, success=True))
            except Exception as e:
                results.append(CompensationResult(
                    compensation=comp,
                    success=False,
                    error=str(e)
                ))
                await self.event_log.append(CompensationExecutedEvent(comp, success=False, error=str(e)))
                # 补偿失败：记录但继续尝试其他补偿
                # 后续需要人工介入
        
        return RollbackReport(
            task_id=task_id,
            total=len(compensations),
            succeeded=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results,
            needs_manual_intervention=any(not r.success for r in results)
        )
    
    async def recover_from_crash(self, task_id: str):
        """
        从崩溃恢复
        读取Event Log，重建补偿栈状态
        """
        events = await self.event_log.get_compensation_events(task_id)
        # 重建栈状态...
```

### 1.3 ToolRuntime 集成

```python
class ToolRuntime:
    async def execute(self, tool: Tool, input: dict, context: ExecutionContext) -> ToolResult:
        # ... 权限检查等 ...
        
        # 写操作必须先获取WritePermit
        if tool.risk_level >= RiskLevel.IDEMPOTENT_WRITE:
            permit = await self.safety_gate.prepare_write(tool, input, context)
            
            if not permit.allowed:
                raise WriteNotPermitted(permit.reason)
            
            # 记录回滚句柄
            if permit.rollback_handle:
                context.rollback_handle = permit.rollback_handle
        
        # 执行工具
        try:
            result = await self._do_execute(tool, input)
            
            # 成功：压入补偿操作
            if tool.compensate_fn and permit.rollback_handle:
                await self.compensation_stack.push(
                    context.task_id,
                    Compensation(
                        tool=tool.name,
                        rollback_handle=permit.rollback_handle,
                        compensate_fn=tool.compensate_fn,
                        original_input=input,
                        original_output=result
                    )
                )
            
            return result
            
        except Exception as e:
            # 失败：立即回滚本次操作
            if permit.rollback_handle:
                await self.safety_gate.rollback(permit.rollback_handle)
            raise
```

---

## 补充章节 2：Plan Schema + PlanValidator

> **评审问题**："计划不是写作文：你如何证明Plan满足期望且风险可控？"

### 2.1 统一 Plan Schema

```python
@dataclass
class Plan:
    """统一计划结构"""
    plan_id: str
    task_id: str
    created_at: datetime
    created_by: str  # model name
    
    # 期望与验收标准
    expectations: List[Expectation]
    done_criteria: List[DoneCriterion]
    
    # 执行步骤
    steps: List[PlanStep]
    
    # 人工审批点
    human_approval_points: List[ApprovalPoint]
    
    # 元信息
    estimated_duration_minutes: int
    estimated_cost_usd: float
    risk_assessment: RiskAssessment


@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    order: int
    description: str
    
    # 工具信息
    tool: str
    tool_input: dict
    risk_level: RiskLevel
    
    # 前置条件
    preconditions: List[Precondition]
    
    # 回滚信息
    rollback_strategy: RollbackStrategy
    rollback_possible: bool
    
    # 后置检查
    postchecks: List[Postcheck]
    
    # 依赖
    depends_on: List[str]  # step_ids


@dataclass
class Expectation:
    """用户期望"""
    expectation_id: str
    description: str
    priority: str  # MUST / SHOULD / COULD
    verification_method: str  # 如何验证是否满足
    covered_by_steps: List[str]  # 哪些步骤覆盖此期望


@dataclass 
class DoneCriterion:
    """完成标准"""
    criterion_id: str
    validator_name: str  # 使用哪个DoneValidator
    threshold: Optional[float]
    required: bool  # 是否必须通过
```

### 2.2 PlanValidator（计划校验器）

```python
class PlanValidator:
    """
    计划校验器
    在执行前拦截不合格的计划
    """
    
    def __init__(
        self,
        coverage_validator: PlanCoverageValidator,
        risk_gate_validator: RiskGateValidator,
        resource_validator: ResourceValidator,
        policy_engine: PolicyEngine
    ):
        self.validators = [
            coverage_validator,
            risk_gate_validator,
            resource_validator,
        ]
        self.policy_engine = policy_engine
    
    async def validate(self, plan: Plan, context: ExecutionContext) -> PlanValidationResult:
        """
        校验计划
        任一校验失败 = 计划被拒绝
        """
        errors = []
        warnings = []
        
        for validator in self.validators:
            result = await validator.validate(plan, context)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        
        # 检查是否需要人工审批
        needs_approval = self._check_approval_required(plan, context)
        
        return PlanValidationResult(
            approved=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            needs_human_approval=needs_approval,
            approval_reason=self._get_approval_reason(plan) if needs_approval else None
        )


class PlanCoverageValidator:
    """计划覆盖校验器：Plan必须覆盖所有MUST期望"""
    
    async def validate(self, plan: Plan, context: ExecutionContext) -> ValidationResult:
        errors = []
        
        must_expectations = [e for e in plan.expectations if e.priority == "MUST"]
        
        for exp in must_expectations:
            if not exp.covered_by_steps:
                errors.append(ValidationError(
                    code="E_EXPECTATION_NOT_COVERED",
                    message=f"MUST expectation not covered: {exp.description}",
                    expectation_id=exp.expectation_id
                ))
            else:
                # 验证覆盖的步骤确实存在
                step_ids = {s.step_id for s in plan.steps}
                missing = set(exp.covered_by_steps) - step_ids
                if missing:
                    errors.append(ValidationError(
                        code="E_INVALID_COVERAGE_REF",
                        message=f"Expectation references non-existent steps: {missing}",
                        expectation_id=exp.expectation_id
                    ))
        
        return ValidationResult(errors=errors)


class RiskGateValidator:
    """风险门禁校验器：高风险步骤必须有回滚+审批"""
    
    RISK_REQUIREMENTS = {
        RiskLevel.NON_IDEMPOTENT_EFFECT: {
            "rollback_possible": True,        # 必须可回滚
            "human_approval": True,           # 必须人工审批
            "two_phase": True,                # 必须两阶段
            "postchecks_required": True,      # 必须有后置检查
        },
        RiskLevel.COMPENSATABLE: {
            "rollback_possible": True,
            "human_approval": False,          # 可选
            "two_phase": False,
            "postchecks_required": True,
        },
        RiskLevel.IDEMPOTENT_WRITE: {
            "rollback_possible": False,       # 可选（幂等可重试）
            "human_approval": False,
            "two_phase": False,
            "postchecks_required": False,
        },
    }
    
    async def validate(self, plan: Plan, context: ExecutionContext) -> ValidationResult:
        errors = []
        
        for step in plan.steps:
            requirements = self.RISK_REQUIREMENTS.get(step.risk_level, {})
            
            if requirements.get("rollback_possible") and not step.rollback_possible:
                errors.append(ValidationError(
                    code="E_ROLLBACK_REQUIRED",
                    message=f"Step {step.step_id} (risk={step.risk_level}) must have rollback capability",
                    step_id=step.step_id
                ))
            
            if requirements.get("human_approval"):
                # 检查是否有对应的审批点
                approval_point_exists = any(
                    ap.before_step == step.step_id 
                    for ap in plan.human_approval_points
                )
                if not approval_point_exists:
                    errors.append(ValidationError(
                        code="E_APPROVAL_REQUIRED",
                        message=f"Step {step.step_id} (risk={step.risk_level}) requires human approval",
                        step_id=step.step_id
                    ))
            
            if requirements.get("postchecks_required") and not step.postchecks:
                errors.append(ValidationError(
                    code="E_POSTCHECK_REQUIRED",
                    message=f"Step {step.step_id} (risk={step.risk_level}) must have postchecks",
                    step_id=step.step_id
                ))
        
        return ValidationResult(errors=errors)
```

---

## 补充章节 3：Evidence Object 规范

> **评审问题**："你所谓的evidence chain是啥？怎么做到可审计、不可抵赖、可复现？"

### 3.1 Evidence Object 定义

```python
@dataclass
class Evidence:
    """
    证据对象
    原则：可审计、不可抵赖、可复现
    """
    evidence_id: str                      # 全局唯一ID
    
    # 类型与内容
    type: EvidenceType                    # 类型枚举
    uri: str                              # 引用URI（不存原文）
    content_hash: str                     # 内容哈希（防篡改）
    
    # 来源
    generated_by: str                     # 生成者（tool/validator/human）
    source_system: str                    # 来源系统
    
    # 时间与追踪
    timestamp: datetime
    trace_id: str                         # 关联trace
    span_id: str                          # 关联span
    
    # 分类与留存
    classification: DataClassification    # 数据分级
    retention_days: int                   # 留存天数
    
    # 验证信息
    signature: Optional[str]              # 可选签名（高敏感证据）
    verified_by: Optional[str]            # 验证者


class EvidenceType(Enum):
    """证据类型枚举"""
    # 执行证据
    TOOL_OUTPUT = "tool_output"           # 工具输出
    COMMAND_LOG = "command_log"           # 命令日志
    FILE_DIFF = "file_diff"               # 文件差异
    GIT_COMMIT = "git_commit"             # Git提交
    
    # 验证证据
    TEST_REPORT = "test_report"           # 测试报告
    BUILD_LOG = "build_log"               # 构建日志
    LINT_RESULT = "lint_result"           # Lint结果
    RULE_ENGINE_RESULT = "rule_engine"    # 规则引擎结果
    RECONCILIATION = "reconciliation"     # 对账结果
    
    # 决策证据
    LLM_RESPONSE = "llm_response"         # LLM响应
    HUMAN_APPROVAL = "human_approval"     # 人工审批
    POLICY_CHECK = "policy_check"         # 策略检查结果
    
    # 外部证据
    EXTERNAL_API = "external_api"         # 外部API响应
    DOCUMENT_REF = "document_ref"         # 文档引用
```

### 3.2 EvidenceStore

```python
class EvidenceStore:
    """
    证据存储
    原则：只存引用和哈希，不存敏感原文
    """
    
    def __init__(self, storage: Storage, policy_engine: PolicyEngine):
        self.storage = storage
        self.policy_engine = policy_engine
    
    async def store(self, evidence: Evidence, content: bytes) -> str:
        """
        存储证据
        1. 计算哈希
        2. 根据分级决定存储方式
        3. 返回URI
        """
        # 计算内容哈希
        content_hash = hashlib.sha256(content).hexdigest()
        
        # 验证哈希匹配
        if evidence.content_hash and evidence.content_hash != content_hash:
            raise EvidenceTampered(f"Hash mismatch: expected {evidence.content_hash}, got {content_hash}")
        
        evidence.content_hash = content_hash
        
        # 根据分级决定存储策略
        storage_policy = self.policy_engine.get_evidence_storage_policy(evidence.classification)
        
        if storage_policy.store_content:
            # 低敏感度：存储内容
            uri = await self._store_content(content, evidence.classification)
        else:
            # 高敏感度：只存引用和哈希
            uri = await self._store_reference_only(evidence)
        
        evidence.uri = uri
        
        # 存储证据元数据
        await self.storage.put(f"evidence:{evidence.evidence_id}", evidence)
        
        return uri
    
    async def verify(self, evidence_id: str) -> VerificationResult:
        """
        验证证据完整性
        1. 检查哈希
        2. 检查签名（如有）
        3. 检查trace关联
        """
        evidence = await self.storage.get(f"evidence:{evidence_id}")
        
        if not evidence:
            return VerificationResult(valid=False, reason="Evidence not found")
        
        # 验证哈希
        if evidence.uri.startswith("content://"):
            content = await self._get_content(evidence.uri)
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != evidence.content_hash:
                return VerificationResult(valid=False, reason="Hash mismatch - content tampered")
        
        # 验证签名
        if evidence.signature:
            if not self._verify_signature(evidence):
                return VerificationResult(valid=False, reason="Signature invalid")
        
        return VerificationResult(valid=True, evidence=evidence)
    
    async def get_chain(self, trace_id: str) -> List[Evidence]:
        """获取完整证据链（按时间排序）"""
        evidences = await self.storage.query(f"evidence:*", filter={"trace_id": trace_id})
        return sorted(evidences, key=lambda e: e.timestamp)
```

### 3.3 DecisionRecord 与 Evidence 的关系

```python
@dataclass
class DecisionRecord:
    """
    决策记录
    原则：只引用Evidence，不内嵌敏感原文
    """
    decision_id: str
    timestamp: datetime
    task_ref: str
    
    # 决策内容
    action: str
    action_params_hash: str  # 参数哈希，不存原文
    
    # 证据引用（不是内嵌）
    evidence_refs: List[str]  # evidence_ids
    
    # 推理摘要（短，<200字，已脱敏）
    reasoning_summary: str
    
    # ... 其他字段 ...


# 使用示例
async def record_decision(
    action: Action,
    evidences: List[Evidence],
    reasoning: str,
    context: ExecutionContext
) -> DecisionRecord:
    """记录决策"""
    # 1. 存储证据
    evidence_ids = []
    for ev in evidences:
        await evidence_store.store(ev, ev.raw_content)
        evidence_ids.append(ev.evidence_id)
    
    # 2. 创建决策记录（只引用证据）
    record = DecisionRecord(
        decision_id=generate_id(),
        timestamp=now(),
        task_ref=context.task_id,
        action=action.name,
        action_params_hash=hash_canonical(action.params),
        evidence_refs=evidence_ids,  # 只存引用
        reasoning_summary=summarize(reasoning, max_chars=200),
        # ...
    )
    
    # 3. 写入Event Log
    await event_log.append(DecisionRecordedEvent(record))
    
    return record
```

---

## 补充章节 4：Approval Protocol（审批协议）

> **评审问题**："人在回路到底怎么做？审批的权限、双人复核、紧急放行怎么落地？"

### 4.1 Approval 作为一等公民

```python
@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    task_id: str
    requested_at: datetime
    requested_by: str  # agent_id
    
    # 审批内容
    action_to_approve: str
    action_params_hash: str
    risk_level: RiskLevel
    impact_summary: str
    
    # 证据
    evidence_refs: List[str]
    dry_run_result: Optional[dict]  # 预演结果
    
    # 审批要求
    required_approvers: int  # 需要几人审批
    required_roles: List[str]  # 需要什么角色
    expires_at: datetime  # 过期时间
    
    # 状态
    status: ApprovalStatus  # PENDING / APPROVED / REJECTED / EXPIRED


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Approval:
    """审批记录"""
    approval_id: str
    request_id: str
    
    # 审批人
    approver: str
    approver_role: str
    approved_at: datetime
    
    # 决定
    decision: str  # APPROVE / REJECT
    reason: Optional[str]
    conditions: Optional[List[str]]  # 附加条件
    
    # 证据
    signature: str  # 审批人签名


class ApprovalProtocol:
    """审批协议"""
    
    def __init__(self, event_log: EventLog, policy_engine: PolicyEngine):
        self.event_log = event_log
        self.policy_engine = policy_engine
    
    async def request_approval(
        self,
        action: Action,
        context: ExecutionContext,
        dry_run_result: Optional[dict] = None
    ) -> ApprovalRequest:
        """请求审批"""
        # 确定审批要求
        requirements = self.policy_engine.get_approval_requirements(
            action.risk_level,
            context
        )
        
        request = ApprovalRequest(
            request_id=generate_id(),
            task_id=context.task_id,
            requested_at=now(),
            requested_by=context.agent_id,
            action_to_approve=action.name,
            action_params_hash=hash_canonical(action.params),
            risk_level=action.risk_level,
            impact_summary=self._generate_impact_summary(action, dry_run_result),
            evidence_refs=context.evidence_refs,
            dry_run_result=dry_run_result,
            required_approvers=requirements.min_approvers,
            required_roles=requirements.required_roles,
            expires_at=now() + timedelta(seconds=requirements.ttl_seconds),
            status=ApprovalStatus.PENDING
        )
        
        # 写入Event Log
        await self.event_log.append(ApprovalRequestedEvent(request))
        
        # 通知审批人
        await self._notify_approvers(request, requirements)
        
        return request
    
    async def approve(
        self,
        request_id: str,
        approver: str,
        approver_role: str,
        reason: Optional[str] = None,
        conditions: Optional[List[str]] = None
    ) -> Approval:
        """审批通过"""
        request = await self._get_request(request_id)
        
        # 检查审批人权限
        if not self.policy_engine.can_approve(approver, approver_role, request):
            raise ApprovalDenied(f"{approver} cannot approve this request")
        
        # 检查是否过期
        if now() > request.expires_at:
            raise ApprovalExpired(request_id)
        
        # 创建审批记录
        approval = Approval(
            approval_id=generate_id(),
            request_id=request_id,
            approver=approver,
            approver_role=approver_role,
            approved_at=now(),
            decision="APPROVE",
            reason=reason,
            conditions=conditions,
            signature=self._sign(approver, request_id, "APPROVE")
        )
        
        # 写入Event Log
        await self.event_log.append(ApprovalGrantedEvent(approval))
        
        # 检查是否满足审批要求
        all_approvals = await self._get_approvals(request_id)
        if self._meets_requirements(request, all_approvals):
            await self._mark_approved(request)
        
        return approval
    
    async def reject(self, request_id: str, rejector: str, reason: str) -> Approval:
        """审批拒绝"""
        # ... 类似approve ...
        pass
    
    async def break_glass(
        self,
        request_id: str,
        operator: str,
        justification: str,
        supervisor_approval: str
    ) -> BreakGlassRecord:
        """
        紧急放行（Break Glass）
        绕过正常审批流程，但必须：
        1. 有supervisor授权
        2. 记录完整审计
        3. 触发告警
        """
        # 验证supervisor授权
        if not self.policy_engine.verify_supervisor(supervisor_approval):
            raise InvalidSupervisorApproval()
        
        record = BreakGlassRecord(
            record_id=generate_id(),
            request_id=request_id,
            operator=operator,
            justification=justification,
            supervisor_approval=supervisor_approval,
            timestamp=now()
        )
        
        # 写入Event Log（高优先级审计）
        await self.event_log.append(BreakGlassEvent(record))
        
        # 触发告警
        await self._alert_break_glass(record)
        
        # 标记请求为已批准（紧急）
        await self._mark_approved_emergency(request_id, record)
        
        return record


# 审批要求配置
class ApprovalRequirements:
    """审批要求"""
    
    # 基于风险级别的默认要求
    DEFAULTS = {
        RiskLevel.NON_IDEMPOTENT_EFFECT: {
            "min_approvers": 1,
            "required_roles": ["operator"],
            "ttl_seconds": 3600,  # 1小时
        },
        # 金融场景：双人复核
        "financial_transaction": {
            "min_approvers": 2,  # 四眼原则
            "required_roles": ["operator", "reviewer"],
            "ttl_seconds": 1800,  # 30分钟
            "same_person_forbidden": True,  # 不能同一人
        },
        # 高风险操作
        "high_risk": {
            "min_approvers": 2,
            "required_roles": ["operator", "security_officer"],
            "ttl_seconds": 900,  # 15分钟
            "requires_mfa": True,
        },
    }
```

---

## 补充章节 5：Validation Policy 降级策略 + Failure Taxonomy

> **评审问题**："验证器不可靠怎么办？外部系统抖动/超时/flake，会不会把流程卡死或误放行？"

### 5.1 Failure Taxonomy（失败码体系）

```python
class FailureCode(Enum):
    """
    统一失败码
    决定后续处理策略（重试/修复/升级/人工）
    """
    
    # === 可自动修复的失败 ===
    E_BUILD_FAIL = "E_BUILD_FAIL"              # 构建失败 → 触发修复
    E_TEST_FAIL = "E_TEST_FAIL"                # 测试失败 → 触发修复
    E_LINT_FAIL = "E_LINT_FAIL"                # Lint失败 → 触发修复
    E_TYPE_ERROR = "E_TYPE_ERROR"              # 类型错误 → 触发修复
    
    # === 需要重试的失败 ===
    E_TOOL_TIMEOUT = "E_TOOL_TIMEOUT"          # 工具超时 → 重试
    E_RATE_LIMIT = "E_RATE_LIMIT"              # 限流 → 等待重试
    E_TRANSIENT_ERROR = "E_TRANSIENT_ERROR"    # 临时错误 → 重试
    
    # === 需要升级模型的失败 ===
    E_MODEL_INSUFFICIENT = "E_MODEL_INSUFFICIENT"  # 模型能力不足 → 升级
    E_CONTEXT_OVERFLOW = "E_CONTEXT_OVERFLOW"      # 上下文溢出 → 升级或分解
    
    # === 需要人工介入的失败 ===
    E_POLICY_DENY = "E_POLICY_DENY"            # 策略拒绝 → 人工审批
    E_EGRESS_BLOCKED = "E_EGRESS_BLOCKED"      # 出站被阻 → 人工处理
    E_APPROVAL_TIMEOUT = "E_APPROVAL_TIMEOUT"  # 审批超时 → 人工跟进
    E_COMPENSATION_FAIL = "E_COMPENSATION_FAIL"  # 补偿失败 → 人工介入
    
    # === 验证器相关 ===
    E_VALIDATOR_TIMEOUT = "E_VALIDATOR_TIMEOUT"  # 验证器超时 → 降级
    E_VALIDATOR_FLAKY = "E_VALIDATOR_FLAKY"      # 验证器不稳定 → 降级
    E_VALIDATOR_UNAVAILABLE = "E_VALIDATOR_UNAVAILABLE"  # 验证器不可用 → 降级
    
    # === 致命错误 ===
    E_UNKNOWN = "E_UNKNOWN"                    # 未知错误 → 停止
    E_SECURITY_VIOLATION = "E_SECURITY_VIOLATION"  # 安全违规 → 停止+告警


@dataclass
class Failure:
    """失败对象"""
    code: FailureCode
    message: str
    timestamp: datetime
    context: dict
    evidence_refs: List[str]
    recoverable: bool
    suggested_action: str
```

### 5.2 Remediation Engine（修复引擎）

```python
class RemediationEngine:
    """
    修复引擎
    原则：Reflection不是常驻步骤，而是NOT_DONE触发的Handler
    """
    
    # 失败码 → 修复策略映射
    REMEDIATION_STRATEGIES = {
        FailureCode.E_BUILD_FAIL: RemediationStrategy(
            handler="code_fix_handler",
            max_iterations=3,
            escalate_on_failure="human",
            model_upgrade_allowed=True,
        ),
        FailureCode.E_TEST_FAIL: RemediationStrategy(
            handler="test_fix_handler",
            max_iterations=3,
            escalate_on_failure="human",
            model_upgrade_allowed=True,
        ),
        FailureCode.E_TOOL_TIMEOUT: RemediationStrategy(
            handler="retry_handler",
            max_iterations=3,
            backoff_seconds=[1, 5, 30],
            escalate_on_failure="skip_or_human",
        ),
        FailureCode.E_VALIDATOR_FLAKY: RemediationStrategy(
            handler="fallback_validator_handler",
            max_iterations=1,
            escalate_on_failure="human_verification",
        ),
        FailureCode.E_MODEL_INSUFFICIENT: RemediationStrategy(
            handler="model_upgrade_handler",
            max_iterations=2,  # 最多升级2次
            escalate_on_failure="human",
        ),
        # 不可自动修复的
        FailureCode.E_POLICY_DENY: RemediationStrategy(
            handler=None,  # 无自动修复
            escalate_immediately="human_approval",
        ),
        FailureCode.E_SECURITY_VIOLATION: RemediationStrategy(
            handler=None,
            escalate_immediately="security_team",
            halt_execution=True,
        ),
    }
    
    async def handle_failure(
        self,
        failure: Failure,
        context: ExecutionContext
    ) -> RemediationResult:
        """处理失败"""
        strategy = self.REMEDIATION_STRATEGIES.get(failure.code)
        
        if not strategy:
            # 未知失败码
            return RemediationResult(
                success=False,
                action="halt",
                reason=f"No remediation strategy for {failure.code}"
            )
        
        if strategy.halt_execution:
            await self._halt_and_alert(failure, context)
            return RemediationResult(success=False, action="halted")
        
        if strategy.escalate_immediately:
            return await self._escalate(failure, strategy.escalate_immediately, context)
        
        if strategy.handler:
            return await self._run_handler(strategy, failure, context)
        
        return RemediationResult(success=False, action="no_handler")
    
    async def _run_handler(
        self,
        strategy: RemediationStrategy,
        failure: Failure,
        context: ExecutionContext
    ) -> RemediationResult:
        """运行修复处理器"""
        handler = self.handlers[strategy.handler]
        
        for iteration in range(strategy.max_iterations):
            # 记录修复尝试
            await self.event_log.append(RemediationAttemptEvent(
                failure=failure,
                iteration=iteration,
                handler=strategy.handler
            ))
            
            # 是否需要升级模型
            if strategy.model_upgrade_allowed and iteration > 0:
                context = await self._upgrade_model(context)
            
            # 执行修复
            result = await handler.remediate(failure, context)
            
            if result.success:
                # 修复成功：生成plan patch（不是长篇反思）
                plan_patch = await self._generate_plan_patch(result, context)
                
                # 记录Decision Record
                await self._record_remediation_decision(
                    failure=failure,
                    result=result,
                    plan_patch=plan_patch,
                    iteration=iteration
                )
                
                return RemediationResult(
                    success=True,
                    action="continue",
                    plan_patch=plan_patch
                )
            
            # 等待后重试
            if iteration < strategy.max_iterations - 1:
                await asyncio.sleep(strategy.backoff_seconds[iteration] if strategy.backoff_seconds else 1)
        
        # 修复失败：升级
        return await self._escalate(failure, strategy.escalate_on_failure, context)
    
    async def _generate_plan_patch(
        self,
        result: HandlerResult,
        context: ExecutionContext
    ) -> PlanPatch:
        """
        生成计划补丁
        不是长篇"我反思了"，而是具体的修改
        """
        return PlanPatch(
            patch_id=generate_id(),
            original_plan_id=context.plan_id,
            changes=[
                PlanChange(
                    type="modify_step",
                    step_id=result.affected_step_id,
                    new_content=result.fix_content
                )
            ],
            reason=result.fix_summary,  # 简短原因（<100字）
            evidence_refs=result.evidence_refs
        )
```

### 5.3 Validation Degradation Policy（验证降级策略）

```python
class ValidationDegradationPolicy:
    """验证降级策略"""
    
    async def handle_inconclusive(
        self,
        validator_name: str,
        result: ValidationResult,
        context: ExecutionContext
    ) -> DegradationDecision:
        """处理INCONCLUSIVE状态"""
        
        # 获取验证器健康状态
        health = await self.flaky_manager.get_health(validator_name)
        
        if health.status == "healthy":
            # 健康验证器的INCONCLUSIVE：等待重试
            return DegradationDecision(
                action="retry",
                wait_seconds=result.retry_after or 60,
                max_retries=3
            )
        
        elif health.status == "degraded":
            # 降级验证器：尝试备用验证器
            fallback = self.get_fallback_validator(validator_name)
            if fallback:
                return DegradationDecision(
                    action="fallback",
                    fallback_validator=fallback
                )
            else:
                # 无备用：转人工
                return DegradationDecision(
                    action="human_verification",
                    reason=f"Validator {validator_name} degraded, no fallback available"
                )
        
        else:  # unavailable
            # 不可用验证器：直接转人工
            return DegradationDecision(
                action="human_verification",
                reason=f"Validator {validator_name} unavailable"
            )
    
    async def handle_not_done(
        self,
        failure: Failure,
        context: ExecutionContext
    ) -> DegradationDecision:
        """处理NOT_DONE状态"""
        
        # 检查是否超过最大修复次数
        remediation_count = await self._get_remediation_count(context.task_id)
        
        if remediation_count >= self.max_remediations:
            return DegradationDecision(
                action="halt",
                reason=f"Max remediation attempts ({self.max_remediations}) exceeded"
            )
        
        # 检查是否可自动修复
        if failure.recoverable:
            return DegradationDecision(
                action="remediate",
                failure_code=failure.code
            )
        
        # 不可自动修复：转人工
        return DegradationDecision(
            action="human_intervention",
            failure=failure
        )
```

---

## 补充章节 6：Hard Enforcement Points（硬拦截点）

> **评审问题**："你怎么防止越权与绕过？"

### 6.1 不可绕过的三条铁律

```python
"""
硬拦截点 - 框架级强制，不可绕过
"""

# 铁律1：所有LLM调用必须走EgressGateway
# 禁止直接调用 litellm.completion() 或 openai.chat()

class ModelClient:
    """唯一的模型调用入口"""
    
    def __init__(self, egress_gateway: EgressGateway):
        self._egress_gateway = egress_gateway
        # 不暴露底层client
    
    async def completion(self, prompt: str, model: str, context: ExecutionContext) -> str:
        """所有调用都经过EgressGateway"""
        return await self._egress_gateway.send(
            destination=self._get_destination(model),
            payload={"prompt": prompt, "model": model},
            context=context
        )


# 铁律2：所有工具调用必须走ToolRuntime
# 禁止直接调用工具函数

class ToolRegistry:
    """工具注册表 - 只能通过ToolRuntime调用"""
    
    def __init__(self):
        self._tools = {}  # 私有，不直接暴露
    
    def register(self, tool: Tool):
        """注册工具（经过合同校验）"""
        self._validate_contract(tool)
        self._tools[tool.name] = tool
    
    def _get_tool(self, name: str) -> Tool:
        """内部方法，只有ToolRuntime能调用"""
        return self._tools.get(name)


class ToolRuntime:
    """唯一的工具执行入口"""
    
    async def execute(self, tool_name: str, input: dict, context: ExecutionContext) -> ToolResult:
        """所有工具调用都经过这里"""
        tool = self._registry._get_tool(tool_name)
        # ... 权限检查、幂等检查、审计等 ...


# 铁律3：所有技能脚本必须走Sandbox
# 禁止宿主机exec

class SkillExecutor:
    """技能脚本执行器"""
    
    def __init__(self, sandbox: SkillSandbox):
        self._sandbox = sandbox
    
    async def execute_script(self, script_path: str, args: dict) -> ScriptResult:
        """所有脚本都在沙箱中执行"""
        return await self._sandbox.execute_script(script_path, args)
    
    # 禁止以下方法
    # subprocess.run() ❌
    # os.system() ❌
    # exec() ❌
```

### 6.2 Bash/Shell 工具的最危险命令控制

```python
class BashTool(Tool):
    """Bash工具 - 最危险的工具之一"""
    
    # 命令黑名单（绝对禁止）
    COMMAND_DENYLIST = [
        # 网络工具（防止数据外传）
        r"curl\s",
        r"wget\s",
        r"ssh\s",
        r"scp\s",
        r"nc\s",
        r"netcat\s",
        r"socat\s",
        r"ncat\s",
        
        # 危险文件操作
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+\*",
        r"chmod\s+777",
        r"chmod\s+-R\s+777",
        r"chown\s+-R",
        
        # 权限提升
        r"sudo\s",
        r"su\s+-",
        r"doas\s",
        
        # 系统操作
        r"shutdown",
        r"reboot",
        r"init\s+0",
        r"systemctl\s+stop",
        
        # 环境污染
        r"export\s+PATH=",
        r"alias\s+",
        
        # 敏感文件访问
        r"cat\s+/etc/passwd",
        r"cat\s+/etc/shadow",
        r"cat\s+~/.ssh/",
    ]
    
    # 路径白名单（只能在这些目录下操作）
    PATH_ALLOWLIST = [
        "/workspace",
        "/tmp/agent_workspace",
        # 明确禁止其他路径
    ]
    
    async def execute(self, command: str, context: ExecutionContext) -> ToolResult:
        """执行bash命令"""
        # 1. 命令黑名单检查
        for pattern in self.COMMAND_DENYLIST:
            if re.search(pattern, command, re.IGNORECASE):
                raise CommandDenied(f"Command matches deny pattern: {pattern}")
        
        # 2. 路径检查（命令中涉及的所有路径必须在白名单内）
        paths = self._extract_paths(command)
        for path in paths:
            abs_path = os.path.abspath(path)
            if not any(abs_path.startswith(allowed) for allowed in self.PATH_ALLOWLIST):
                raise PathDenied(f"Path not in allowlist: {path}")
        
        # 3. 在受限环境中执行
        result = await self._execute_in_sandbox(command, context)
        
        # 4. 输出脱敏
        sanitized_output = self.policy_engine.apply_redaction(
            result.stdout,
            DataClassification.INTERNAL,
            purpose="tool_output"
        )
        
        return ToolResult(
            success=result.exit_code == 0,
            stdout=sanitized_output,
            stderr=result.stderr,
            exit_code=result.exit_code
        )


class FileTool(Tool):
    """文件工具 - 路径白名单控制"""
    
    # 写入路径白名单
    WRITE_ALLOWLIST = [
        "/workspace",
        "/tmp/agent_workspace",
    ]
    
    # 绝对禁止访问的路径
    PATH_DENYLIST = [
        "/etc",
        "/var",
        "/home",
        "/root",
        "~",
        "..",  # 防止路径遍历
    ]
    
    async def write_file(self, path: str, content: str, context: ExecutionContext) -> ToolResult:
        """写入文件"""
        abs_path = os.path.abspath(path)
        
        # 检查禁止路径
        for denied in self.PATH_DENYLIST:
            if denied in path or denied in abs_path:
                raise PathDenied(f"Path contains denied pattern: {denied}")
        
        # 检查白名单
        if not any(abs_path.startswith(allowed) for allowed in self.WRITE_ALLOWLIST):
            raise PathDenied(f"Write path not in allowlist: {path}")
        
        # 执行写入
        # ...
```

### 6.3 架构强制点总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Hard Enforcement Points                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  入口层（所有请求必须从这里进入）                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  API Gateway / Request Handler                               │   │
│  │  • 身份认证                                                  │   │
│  │  • 请求签名验证                                              │   │
│  │  • Rate limiting                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  执行层（三个不可绕过的门）                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │
│  │ Egress Gateway  │ │  Tool Runtime   │ │  Skill Sandbox  │       │
│  │                 │ │                 │ │                 │       │
│  │ 所有LLM调用     │ │ 所有工具调用    │ │ 所有脚本执行    │       │
│  │ 必须经过        │ │ 必须经过        │ │ 必须经过        │       │
│  │                 │ │                 │ │                 │       │
│  │ • 数据分级      │ │ • 合同校验      │ │ • 隔离执行      │       │
│  │ • 出站策略      │ │ • 权限检查      │ │ • 资源限制      │       │
│  │ • 脱敏          │ │ • 幂等/补偿     │ │ • 网络隔离      │       │
│  │ • 审计          │ │ • 审计          │ │ • 审计          │       │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘       │
│                              │                                      │
│  存储层（所有状态变更都在这里记录）                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Event Log                                                   │   │
│  │  • Append-only                                               │   │
│  │  • 防篡改                                                    │   │
│  │  • 证据链                                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

绕过检测：
• 所有组件定期自检，检测是否有绕过尝试
• 异常模式检测（如：直接网络请求、非预期文件访问）
• 违规尝试记录到安全审计日志
```

---

## 附录：评审 Q&A

> GPT建议："把这6个问题写成评审Q&A附录，评审会从'找茬模式'切到'你们准备得挺像样模式'"

### Q1: 你怎么保证写操作一定可回滚？

**A**: 
- WorkspaceSafetyGate 在执行前强制创建回滚句柄
- 没有回滚句柄的高风险操作会被拒绝
- 回滚句柄写入 Event Log，崩溃后可恢复
- 补偿栈实现 Saga 模式的逆序撤回
- **证据在 Event Log 的 `rollback_handle` 字段**

### Q2: 你如何证明 Plan 满足期望且风险可控？

**A**:
- Plan Schema 统一定义 expectations、steps、done_criteria
- PlanCoverageValidator 检查所有 MUST 期望是否被覆盖
- RiskGateValidator 检查高风险步骤是否有回滚+审批
- 不通过校验的 Plan 直接被拒绝，不进入执行
- **这是规则，不是建议**

### Q3: 你的 evidence chain 怎么做到可审计、不可抵赖？

**A**:
- Evidence Object 包含：content_hash、signature、trace_id
- EvidenceStore 只存引用和哈希，不存敏感原文
- DecisionRecord 只引用 evidence_ids，不内嵌
- 所有证据可通过 trace_id 关联
- **内容哈希防篡改，签名防抵赖**

### Q4: 人在回路怎么落地？双人复核怎么做？

**A**:
- Approval Protocol 是一等公民，写入 Event Log
- 支持配置：min_approvers、required_roles、TTL
- 金融场景：四眼原则（min_approvers=2）
- Break Glass 机制：需要 supervisor 授权 + 告警
- **所有审批都有签名和完整审计**

### Q5: 验证器不可靠怎么办？

**A**:
- 统一失败码体系（Failure Taxonomy）
- INCONCLUSIVE 状态不会卡死流程
- 降级策略：等待重试 → 备用验证器 → 人工验证
- Flaky 管理：超过阈值自动降级
- **Reflection 不是常驻步骤，是 NOT_DONE 触发的 Handler**

### Q6: 你怎么防止越权与绕过？

**A**:
- 三条铁律：LLM必须走EgressGateway、工具必须走ToolRuntime、脚本必须走Sandbox
- Bash 命令黑名单 + 路径白名单
- 文件操作路径白名单
- 所有拦截都有审计记录
- **这是架构强制，不是约定**

---

*文档版本: v2.2*
*状态: 可进入银行级架构评审*
*LangGraph定位: 可选编排层实现，P0组件独立于LangGraph*
