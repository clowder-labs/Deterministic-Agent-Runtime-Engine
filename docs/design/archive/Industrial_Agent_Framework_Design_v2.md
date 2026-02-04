# 工业级 Agent 框架设计文档 v2.0

> 本文档基于多轮技术评审修订，目标是设计一个可落地银行/金融/代码生成场景的 Agent 框架。

---

## 一、设计原则

从 Anthropic 的 Skills 范式、Long-running Agent Harness、以及分布式系统工程实践中提炼：

| 原则 | 含义 | 来源 |
|------|------|------|
| **状态外化** | 所有状态存文件/DB/Event Log，不依赖模型记忆 | Anthropic Harness |
| **增量执行** | 每次只做一件事，做完提交，留清晰交接物 | Anthropic Harness |
| **外部可验证** | "完成"由外部信号判定（测试/对账/规则），不信任模型自己说done | 分布式系统 |
| **幂等优先** | 任何操作都可安全重试，不产生重复副作用 | 分布式系统 |
| **模型分层** | 规划用强模型，执行用小模型，成本与质量平衡 | 工程现实 |
| **技能组合** | 通用模型 + 领域技能包，而非"万能agent" | Anthropic Skills |
| **可审计** | 每个决策有结构化记录，可追溯、可解释 | 金融合规 |

---

## 二、核心约束

### 2.1 政治/合规约束

| 约束 | 影响 |
|------|------|
| 不能用阿里系开源 | AgentScope ❌ |
| 不能用 AWS 系开源 | Amazon Bedrock Agents ❌ |
| 可以用 | LangChain/LangGraph ✅, DSPy ✅, Pydantic AI ✅, Google ✅, Temporal ✅ |

### 2.2 业务约束

| 约束 | 影响 |
|------|------|
| 金融场景 | 强审计、合规、敏感数据治理、人在回路 |
| 编码场景 | 容错、迭代、外部验证（build/test/lint） |
| 成本约束 | 不是所有步骤都能用顶级模型 |
| 多模型支持 | 需要支持国产模型、开源模型、商业API |

---

## 三、P0 承重梁（框架级硬约束）

> 这三个组件是"框架能正确运行"的生死线。缺任何一个，生产必爆。

### 3.1 Event Log（事件化状态系统）

**不是存储接口，是"事件化状态 + 语义约束"的系统。**

```python
@dataclass
class Event:
    """每个事件必须包含的字段"""
    event_id: str                    # 全局唯一ID
    idempotency_key: str             # 幂等键（重试不重复执行）
    timestamp: datetime              # 时间戳
    actor: str                       # 执行者（agent/human/system）
    action_type: str                 # 动作类型
    input_canonical_hash: str        # 规范化后的输入hash
    output_summary: str              # 输出摘要（已脱敏）
    evidence_refs: List[str]         # 证据引用（不存原文）
    data_classification: str         # 数据分级（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED）
    causal_parent: Optional[str]     # 因果父事件ID（用于依赖追踪）
    version: str                     # schema版本


class EventLog:
    """Append-only 事件日志"""
    
    def append(self, event: Event) -> None:
        """
        写入前强制检查：
        1. idempotency_key 去重
        2. data_classification 脱敏策略
        3. causal_parent 存在性校验
        """
        # 幂等检查
        if self.exists(event.idempotency_key):
            return  # 已存在，跳过
        
        # 数据分级脱敏
        event = self.apply_redaction_policy(event)
        
        # 因果链校验
        if event.causal_parent and not self.exists(event.causal_parent):
            raise CausalityViolation(f"Parent {event.causal_parent} not found")
        
        self._storage.append(event)
    
    def replay_from(self, checkpoint: str) -> State:
        """从检查点重放状态"""
        pass
    
    def snapshot(self) -> Snapshot:
        """
        定期快照，解决事件无限增长问题
        快照后旧事件可归档/压缩
        """
        pass
```

**关键设计决策：**

| 问题 | 解决方案 |
|------|---------|
| 事件无限增长 | 定期 snapshot + 归档，replay 从最近快照开始 |
| 敏感数据落盘 | data_classification 字段 + 脱敏策略，不存原文只存引用 |
| input hash 漂移 | 输入必须 canonicalization（字段排序、去噪、去动态字段）后再 hash |
| 多 agent 并发写 | 定义写入权限 + 乐观锁 + 因果链编码 |
| 与 Temporal 关系 | Temporal history = 执行真相源；Event Log = 业务真相源；两者并存但有主从 |

---

### 3.2 Tool Runtime（分级工具运行时）

**不能一刀切要求所有工具都有补偿函数。按风险级别强制不同合同。**

```python
class RiskLevel(Enum):
    """工具风险分级"""
    READ_ONLY = "read_only"                      # 只读，无副作用
    IDEMPOTENT_WRITE = "idempotent_write"        # 幂等写入
    NON_IDEMPOTENT_EFFECT = "non_idempotent"     # 不可幂等副作用
    COMPENSATABLE = "compensatable"              # 可补偿


# 不同风险级别的合同要求
TOOL_CONTRACTS = {
    RiskLevel.READ_ONLY: {
        "required": ["permission_scope", "timeout", "output_schema"],
        "optional": ["retry_policy"],
        "forbidden": ["compensate_fn"],  # 不需要
    },
    RiskLevel.IDEMPOTENT_WRITE: {
        "required": ["permission_scope", "timeout", "output_schema", 
                     "idempotency_key_fn", "retry_policy"],
        "optional": ["compensate_fn"],
    },
    RiskLevel.NON_IDEMPOTENT_EFFECT: {
        "required": ["permission_scope", "timeout", "output_schema",
                     "dry_run_fn", "human_approval_required"],  # 必须两阶段
        "optional": [],
        "max_auto_retry": 0,  # 不能自动重试
    },
    RiskLevel.COMPENSATABLE: {
        "required": ["permission_scope", "timeout", "output_schema",
                     "idempotency_key_fn", "retry_policy", "compensate_fn"],
        "optional": [],
    },
}


class ToolRuntime:
    """工具执行运行时"""
    
    def register(self, tool: Tool) -> None:
        """注册时根据风险级别校验合同"""
        contract = TOOL_CONTRACTS[tool.risk_level]
        
        for field in contract["required"]:
            if not hasattr(tool, field) or getattr(tool, field) is None:
                raise ContractViolation(
                    f"Tool {tool.name} (risk={tool.risk_level}) "
                    f"missing required field: {field}"
                )
    
    async def execute(self, tool: Tool, input: dict, context: ExecutionContext) -> ToolResult:
        """执行时根据风险级别走不同流程"""
        
        # 1. 权限检查（所有级别都需要）
        if not self.policy_engine.check_permission(tool.permission_scope, context):
            raise PermissionDenied()
        
        # 2. 根据风险级别分流
        if tool.risk_level == RiskLevel.READ_ONLY:
            return await self._execute_readonly(tool, input, context)
        
        elif tool.risk_level == RiskLevel.IDEMPOTENT_WRITE:
            return await self._execute_idempotent(tool, input, context)
        
        elif tool.risk_level == RiskLevel.NON_IDEMPOTENT_EFFECT:
            return await self._execute_two_phase(tool, input, context)
        
        elif tool.risk_level == RiskLevel.COMPENSATABLE:
            return await self._execute_with_saga(tool, input, context)
    
    async def _execute_two_phase(self, tool: Tool, input: dict, context: ExecutionContext) -> ToolResult:
        """不可幂等副作用：必须两阶段 + 人在回路"""
        # Phase 1: Dry run
        dry_run_result = await tool.dry_run_fn(input)
        
        # Phase 2: Human approval
        if tool.human_approval_required:
            approval = await self.request_human_approval(
                tool=tool,
                input=input,
                dry_run_result=dry_run_result,
                context=context
            )
            if not approval.approved:
                return ToolResult(status="REJECTED", reason=approval.reason)
        
        # Phase 3: Commit
        return await tool.execute(input)
```

---

### 3.3 Done Validator（外部可验证完成判定）

**"完成"不能靠模型说，必须由外部可验证信号判定。**

```python
class DoneStatus(Enum):
    """完成状态 - 允许不确定状态"""
    DONE = "done"                    # 确定完成
    NOT_DONE = "not_done"            # 确定未完成
    INCONCLUSIVE = "inconclusive"    # 不确定（验证系统抽风/数据未到齐）


@dataclass
class ValidationResult:
    status: DoneStatus
    validator_name: str
    evidence: List[str]              # 证据链
    failure_reason: Optional[str]
    retry_after: Optional[int]       # INCONCLUSIVE时建议等待秒数


class DoneValidator:
    """完成判定器 - 组合多个外部验证器"""
    
    def __init__(self, validators: List[Validator], policy: ValidationPolicy):
        """
        validators 示例：
        - 编码场景: BuildValidator, TestValidator, LintValidator, SmokeTestValidator
        - 金融场景: RuleEngineValidator, ReconciliationValidator, RiskThresholdValidator
        
        policy 定义：
        - 全部通过才算DONE？还是关键验证器通过即可？
        - INCONCLUSIVE时的处理策略
        """
        self.validators = validators
        self.policy = policy
    
    async def validate(self, task: Task, result: Result) -> DoneResult:
        """
        注意: 这里不调用LLM判断"是否完成"
        而是调用外部可验证系统
        """
        results = []
        
        for validator in self.validators:
            try:
                check = await asyncio.wait_for(
                    validator.validate(task, result),
                    timeout=validator.timeout
                )
                results.append(check)
            except asyncio.TimeoutError:
                results.append(ValidationResult(
                    status=DoneStatus.INCONCLUSIVE,
                    validator_name=validator.name,
                    evidence=[],
                    failure_reason="Validator timeout",
                    retry_after=60
                ))
        
        # 根据 policy 聚合结果
        return self.policy.aggregate(results)


# 验证策略示例
class StrictValidationPolicy(ValidationPolicy):
    """严格策略：全部DONE才算DONE，任一INCONCLUSIVE则等待"""
    
    def aggregate(self, results: List[ValidationResult]) -> DoneResult:
        if any(r.status == DoneStatus.NOT_DONE for r in results):
            return DoneResult(
                is_done=False,
                status=DoneStatus.NOT_DONE,
                failures=[r for r in results if r.status == DoneStatus.NOT_DONE],
                evidence=self._collect_evidence(results)
            )
        
        if any(r.status == DoneStatus.INCONCLUSIVE for r in results):
            return DoneResult(
                is_done=False,
                status=DoneStatus.INCONCLUSIVE,
                retry_after=max(r.retry_after or 60 for r in results if r.status == DoneStatus.INCONCLUSIVE),
                evidence=self._collect_evidence(results)
            )
        
        return DoneResult(
            is_done=True,
            status=DoneStatus.DONE,
            evidence=self._collect_evidence(results)
        )
```

---

## 四、P0.5 安全与数据治理总开关

> GPT 第二轮反馈的关键补充：Policy/数据分级/权限模型要像电源总闸一样贯穿所有组件。

```python
class PolicyEngine:
    """
    安全与数据治理总开关
    贯穿 Event Log、Skills、Tool Runtime、Decision Record
    """
    
    def __init__(self, config: PolicyConfig):
        self.data_classification_rules = config.data_classification_rules
        self.permission_matrix = config.permission_matrix
        self.redaction_policies = config.redaction_policies
        self.retention_policies = config.retention_policies
    
    # ===== 数据分级 =====
    def classify_data(self, data: Any, context: ExecutionContext) -> DataClassification:
        """
        分级：PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
        根据数据内容、来源、上下文自动分级
        """
        pass
    
    def apply_redaction(self, data: Any, classification: DataClassification, 
                        purpose: str) -> Any:
        """
        根据分级和用途脱敏
        - 写入 Event Log：CONFIDENTIAL 以上只存引用
        - 返回给用户：根据用户权限决定
        - 发送给外部模型：按 DLP 策略处理
        """
        pass
    
    # ===== 权限控制 =====
    def check_permission(self, scope: PermissionScope, context: ExecutionContext) -> bool:
        """
        检查当前 context 是否有权限执行 scope 内的操作
        context 包含：user, agent, session, task, environment
        """
        pass
    
    def get_allowed_tools(self, context: ExecutionContext) -> List[Tool]:
        """根据上下文返回允许使用的工具列表"""
        pass
    
    # ===== 留存策略 =====
    def get_retention_policy(self, data_classification: DataClassification) -> RetentionPolicy:
        """
        不同分级数据的留存策略
        - PUBLIC: 永久
        - INTERNAL: 7年
        - CONFIDENTIAL: 3年，加密存储
        - RESTRICTED: 1年，审批后访问
        """
        pass
```

**PolicyEngine 如何贯穿各组件：**

```
┌─────────────────────────────────────────────────────────────┐
│                      PolicyEngine                            │
│         （数据分级 / 权限控制 / 脱敏策略 / 留存策略）          │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Event Log    │   │ Tool Runtime  │   │ Skill Manager │
│               │   │               │   │               │
│ • 写入前分级  │   │ • 执行前权限  │   │ • 加载前签名  │
│ • 写入时脱敏  │   │ • 输出脱敏    │   │ • 内容扫描    │
│ • 留存策略    │   │ • 审计记录    │   │ • 版本控制    │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                ┌───────────────────┐
                │ Decision Record   │
                │                   │
                │ • 结构化（非长文）│
                │ • 证据引用        │
                │ • 分级存储        │
                └───────────────────┘
```

---

## 五、P1 核心能力

### 5.1 Model Router（模型路由与预算管理）

> 在"框架能正确运行"的语义上是 P1，但在"框架能规模化商用"的语义上会很快变成 P0。

```python
class ModelRouter:
    """智能模型选择与预算管理"""
    
    def __init__(self, config: RouterConfig, budget_manager: BudgetManager):
        self.routing_rules = config.routing_rules
        self.budget_manager = budget_manager
        self.fallback_chain = config.fallback_chain
    
    async def select_and_call(
        self, 
        task_type: TaskType,
        prompt: str,
        context: ExecutionContext
    ) -> LLMResponse:
        """
        1. 根据任务类型和复杂度选择模型
        2. 检查预算
        3. 调用，失败则降级
        """
        # 估算复杂度
        complexity = await self.estimate_complexity(prompt, context)
        
        # 选择模型
        model = self.select_model(task_type, complexity)
        
        # 预算检查
        if not self.budget_manager.can_afford(model, estimated_tokens=len(prompt)):
            model = self.budget_manager.get_affordable_alternative(model)
        
        # 调用（带降级）
        try:
            return await self.call_with_timeout(model, prompt)
        except (RateLimitError, ServiceUnavailable) as e:
            return await self.fallback(model, prompt, context)
    
    def select_model(self, task_type: TaskType, complexity: float) -> str:
        """
        路由策略示例：
        - PLANNING + high complexity → claude-opus-4
        - PLANNING + medium complexity → claude-sonnet-4
        - EXECUTION + any → gpt-4o-mini 或更小
        - REFLECTION + high → claude-sonnet-4
        - REFLECTION + low → claude-haiku
        - CLASSIFICATION → gpt-4o-mini
        """
        pass


class BudgetManager:
    """预算与配额管理"""
    
    def __init__(self, config: BudgetConfig):
        self.daily_budget = config.daily_budget
        self.per_task_budget = config.per_task_budget
        self.model_quotas = config.model_quotas  # 每个模型的配额
    
    def can_afford(self, model: str, estimated_tokens: int) -> bool:
        """检查是否在预算内"""
        pass
    
    def record_usage(self, model: str, tokens: int, cost: float) -> None:
        """记录使用量"""
        pass
    
    def get_affordable_alternative(self, preferred_model: str) -> str:
        """预算不足时的替代方案"""
        pass
```

---

### 5.2 Decision Recorder（结构化决策记录）

> 不是"长篇反思"，而是短、结构化、可审计的决策记录。

```python
@dataclass
class DecisionRecord:
    """
    结构化决策记录
    设计原则：短、可审计、不存敏感原文
    """
    decision_id: str
    timestamp: datetime
    task_ref: str                           # 任务引用
    
    # 决策内容
    action: str                             # 执行的动作
    action_params_hash: str                 # 参数hash（不存原文）
    
    # 推理依据（简短）
    evidence_refs: List[str]                # 证据引用列表
    reasoning_summary: str                  # 推理摘要（<200字）
    confidence: float                       # 置信度
    
    # 风险与回滚
    risk_flags: List[str]                   # 风险标记
    rollback_plan_ref: Optional[str]        # 回滚计划引用
    
    # 元信息
    model_used: str                         # 使用的模型
    latency_ms: int                         # 延迟
    data_classification: str                # 数据分级


class DecisionRecorder:
    """决策记录器"""
    
    def __init__(self, event_log: EventLog, policy_engine: PolicyEngine):
        self.event_log = event_log
        self.policy_engine = policy_engine
    
    async def record(
        self,
        task: Task,
        action: Action,
        reasoning: str,
        evidence: List[Evidence],
        context: ExecutionContext
    ) -> DecisionRecord:
        """
        记录决策
        1. 压缩 reasoning 到摘要
        2. 只存证据引用，不存原文
        3. 根据分级脱敏
        4. 写入 Event Log
        """
        # 压缩推理到摘要（不超过200字）
        reasoning_summary = await self.summarize_reasoning(reasoning, max_chars=200)
        
        # 提取证据引用
        evidence_refs = [e.ref for e in evidence]
        
        # 创建记录
        record = DecisionRecord(
            decision_id=generate_id(),
            timestamp=now(),
            task_ref=task.id,
            action=action.name,
            action_params_hash=hash_canonical(action.params),
            evidence_refs=evidence_refs,
            reasoning_summary=reasoning_summary,
            confidence=action.confidence,
            risk_flags=self.extract_risk_flags(action, context),
            rollback_plan_ref=action.rollback_plan_id,
            model_used=context.model,
            latency_ms=context.latency_ms,
            data_classification=self.policy_engine.classify_data(record, context)
        )
        
        # 脱敏后写入
        redacted_record = self.policy_engine.apply_redaction(
            record, 
            record.data_classification,
            purpose="audit_log"
        )
        
        await self.event_log.append(self.to_event(redacted_record))
        
        return record
```

---

### 5.3 Skill Manager（技能管理 + 供应链治理）

> Skills 如果不上治理，会变成 prompt/tool 注入的温床。

```python
class SkillManager:
    """
    技能管理器
    实现 Anthropic 的 Skills 范式 + 企业级供应链治理
    """
    
    def __init__(
        self, 
        skills_dir: str, 
        policy_engine: PolicyEngine,
        signature_verifier: SignatureVerifier
    ):
        self.skills_dir = skills_dir
        self.policy_engine = policy_engine
        self.signature_verifier = signature_verifier
        self.skill_index = {}  # 懒加载索引
    
    # ===== 供应链治理 =====
    
    def register_skill(self, skill_path: str, metadata: SkillMetadata) -> None:
        """
        注册技能时的治理检查：
        1. 签名验证（来源可信）
        2. 静态扫描（无恶意内容）
        3. 权限声明审核
        4. 版本锁定
        """
        # 1. 签名验证
        if not self.signature_verifier.verify(skill_path, metadata.signature):
            raise SkillSignatureInvalid(f"Skill {skill_path} signature verification failed")
        
        # 2. 静态扫描
        scan_result = self.static_scan(skill_path)
        if scan_result.has_violations:
            raise SkillSecurityViolation(scan_result.violations)
        
        # 3. 权限声明审核
        if not self.policy_engine.approve_skill_permissions(metadata.required_permissions):
            raise SkillPermissionDenied(metadata.required_permissions)
        
        # 4. 注册（版本锁定）
        self.skill_index[metadata.name] = SkillEntry(
            path=skill_path,
            version=metadata.version,
            version_lock=metadata.version_lock,
            triggers=metadata.triggers,
            required_permissions=metadata.required_permissions,
            loaded_at=now()
        )
    
    def static_scan(self, skill_path: str) -> ScanResult:
        """
        静态扫描检查：
        - Prompt injection patterns
        - 敏感信息硬编码
        - 危险系统调用
        - 权限提升尝试
        """
        pass
    
    # ===== Progressive Disclosure =====
    
    def get_skill_index(self) -> List[SkillSummary]:
        """
        返回技能索引（只有名称和描述）
        用于模型初始了解有哪些技能可用
        """
        return [
            SkillSummary(name=s.name, description=s.description, triggers=s.triggers)
            for s in self.skill_index.values()
        ]
    
    async def load_skill(self, name: str, context: ExecutionContext) -> Skill:
        """
        按需加载完整技能内容
        1. 权限检查
        2. 加载 SKILL.md + 引用文件
        3. 记录访问日志
        """
        entry = self.skill_index.get(name)
        if not entry:
            raise SkillNotFound(name)
        
        # 权限检查
        if not self.policy_engine.check_permission(entry.required_permissions, context):
            raise PermissionDenied(f"No permission to use skill {name}")
        
        # 加载
        skill = self._load_full_skill(entry.path)
        
        # 审计
        await self.audit_skill_access(name, context)
        
        return skill
    
    # ===== 灰度与回滚 =====
    
    def enable_canary(self, skill_name: str, new_version: str, percentage: int) -> None:
        """灰度发布新版本技能"""
        pass
    
    def rollback(self, skill_name: str, to_version: str) -> None:
        """回滚到指定版本"""
        pass
```

**SKILL.md 格式规范：**

```yaml
---
# === 元信息 ===
name: financial_compliance
version: 2.1.0
version_lock: true  # 锁定版本，不自动升级
signature: "sha256:abc123..."  # 签名

# === 触发条件 ===
triggers:
  - "合规检查"
  - "风险评估"
  - "交易审核"

# === 权限声明 ===
required_permissions:
  - scope: "read:transactions"
    reason: "需要读取交易记录进行合规检查"
  - scope: "read:customer_profile"
    reason: "需要客户风险等级信息"

# === 依赖 ===
required_context:
  - compliance_rules.md
  - risk_thresholds.json

tools:
  - validate_transaction
  - check_sanctions_list

# === 数据分级 ===
data_classification: CONFIDENTIAL
---

# 金融合规技能

## 何时使用
当需要进行交易合规检查、风险评估时使用此技能。

## 执行流程
1. 读取 compliance_rules.md 了解当前合规要求
2. 获取交易详情和客户风险等级
3. 使用 validate_transaction 工具检查交易
4. 如触发风险阈值，标记需人工复核

## 输出格式
[结构化报告模板]

## 边界与限制
- 不能自动批准超过阈值的交易
- 不能修改客户风险等级
- 所有决策必须有证据引用
```

---

## 六、组件选型矩阵

### 6.1 借用组件

| 组件 | 来源 | 用途 | 集成方式 |
|------|------|------|---------|
| **LiteLLM** | BerriAI | 统一模型接口 | 直接使用 |
| **Instructor** | Jason Liu | 结构化输出 | 直接使用 |
| **Pydantic** | Pydantic | 数据验证 | 直接使用 |
| **DSPy Signature** | Stanford | Prompt 声明式定义 | 参考设计，可能自研 |
| **Temporal** | temporal.io | 持久化执行（可选） | 金融场景考虑引入 |
| **Langfuse** | 开源 | 可观测性 | 直接使用或自部署 |
| **OpenTelemetry** | CNCF | 追踪标准 | 直接使用 |

### 6.2 自研组件

| 组件 | 优先级 | 理由 |
|------|--------|------|
| Event Log | P0 | 核心状态语义，必须自研 |
| Tool Runtime | P0 | 分级合同机制，必须自研 |
| Done Validator | P0 | 外部验证集成，必须自研 |
| Policy Engine | P0.5 | 安全总开关，必须自研 |
| Model Router | P1 | 成本优化核心，必须自研 |
| Decision Recorder | P1 | 审计核心，必须自研 |
| Skill Manager | P1 | 供应链治理，必须自研 |

### 6.3 关于 Temporal 的定位修正

**Temporal 是什么：**
- Durable execution（持久化执行）
- Event history（事件历史）
- Deterministic replay（确定性重放）
- 长事务/异步等待/失败恢复的工业级底座

**Temporal 不是什么：**
- 不是跨外部系统的 ACID 强一致性保证
- 一致性语义需要业务层通过**幂等 + 补偿（Saga）**来实现

**引入 Temporal 的工程纪律：**
- Workflow 里不能有不可重放逻辑（时间戳、随机数、外部请求）
- LLM 调用结果必须作为 activity result 写进事件历史
- 边界必须严格封装，否则会出现重放漂移、重复副作用

**推荐用法：**
- Temporal history = 执行真相源（底层）
- 自研 Event Log = 业务真相源（上层）
- 两者通过 correlation ID 关联，但有明确主从关系

---

## 七、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         应用层 (Applications)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ 金融合规 Agent   │  │ 代码生成 Agent   │  │ 文档处理 Agent   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
├─────────────────────────────────────────────────────────────────────┤
│                      安全与治理层 (Policy Engine)                    │
│         数据分级 │ 权限控制 │ 脱敏策略 │ 留存策略 │ 审计             │
├─────────────────────────────────────────────────────────────────────┤
│                         技能层 (Skills)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ 金融规则     │ │ 代码规范     │ │ 文档模板     │ │ 工具使用     │  │
│  │ SKILL.md    │ │ SKILL.md    │ │ SKILL.md    │ │ SKILL.md    │  │
│  │ (签名+版本)  │ │ (签名+版本)  │ │ (签名+版本)  │ │ (签名+版本)  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         编排层 (Orchestration)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Plan-Execute-Reflect Loop                 │   │
│  │  ┌─────────┐      ┌─────────┐      ┌─────────┐              │   │
│  │  │ Planner │ ──▶  │Executor │ ──▶  │Reflector│ ──┐          │   │
│  │  │(强模型) │      │(小模型) │      │(中模型) │   │          │   │
│  │  └─────────┘      └─────────┘      └─────────┘   │          │   │
│  │       ▲                                          │          │   │
│  │       └──────────────────────────────────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                       P0 承重梁 (Core Runtime)                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │
│  │   Event Log     │ │  Tool Runtime   │ │ Done Validator  │       │
│  │                 │ │                 │ │                 │       │
│  │ • Append-only   │ │ • 分级合同      │ │ • 外部可验证    │       │
│  │ • 幂等键        │ │ • 权限+幂等     │ │ • DONE/NOT_DONE │       │
│  │ • 因果链        │ │ • 两阶段/Saga   │ │ • INCONCLUSIVE  │       │
│  │ • 快照+归档     │ │ • 人在回路      │ │ • 证据链        │       │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│                        基础设施层 (Infrastructure)                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │LiteLLM  │ │Instructor│ │Langfuse │ │  OTel   │ │Temporal │      │
│  │模型接口  │ │结构化输出│ │可观测性  │ │追踪标准 │ │持久化   │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 八、风险矩阵与缓解措施

| 风险 | 严重度 | 缓解措施 |
|------|--------|---------|
| Event Log 敏感数据泄露 | 高 | Policy Engine 强制分级 + 脱敏；只存引用不存原文 |
| Tool 重复执行副作用 | 高 | 幂等键 + 去重；不可幂等操作走两阶段 |
| Skills 注入攻击 | 高 | 签名验证 + 静态扫描 + 权限最小化 |
| 模型幻觉导致错误决策 | 高 | Done Validator 外部验证；人在回路 |
| 成本失控 | 中 | Budget Manager 预算管理；模型分层 |
| Temporal 重放漂移 | 中 | 严格隔离非确定性逻辑到 activity |
| 验证器 Flaky | 中 | INCONCLUSIVE 状态 + 重试机制 |

---

## 九、护城河分析

> GPT 第二轮反馈的洞察：真正的护城河可能不是"又一个 agent 框架"。

### 9.1 短期护城河（6-12个月）

框架本身不是护城河，因为：
- 模型能力快速迭代，框架会被追平
- 开源框架会逐步完善

### 9.2 长期护城河

| 护城河 | 为什么难复制 |
|--------|-------------|
| **企业级 Skill 供应链** | 领域知识积累、合规审核流程、版本治理体系 |
| **可验证 Harness（评测与验收体系）** | 金融/编码场景的验证器积累、基准数据集、持续评测 |
| **审计与合规能力** | 与监管对接、合规认证、数据治理实践 |

**核心观点：**

> 模型换代、框架换皮都不伤筋动骨的东西，才是真护城河。
> 
> 那就是：**领域 Skills + 验证 Harness + 合规能力**

---

## 十、实施路线图

### Phase 1: P0 承重梁（Month 1-2）
- [ ] Event Log 核心实现（幂等、因果链、快照）
- [ ] Tool Runtime 分级合同
- [ ] Done Validator 框架 + 编码场景验证器
- [ ] Policy Engine 基础版（数据分级、权限）

### Phase 2: P1 核心能力（Month 3-4）
- [ ] Model Router + Budget Manager
- [ ] Decision Recorder
- [ ] Skill Manager（含治理）
- [ ] 金融场景验证器集成

### Phase 3: 生产化（Month 5-6）
- [ ] Temporal 集成（可选）
- [ ] 可观测性完善
- [ ] 性能优化
- [ ] 安全审计

### Phase 4: 护城河建设（持续）
- [ ] 领域 Skills 积累
- [ ] 验证 Harness 完善
- [ ] 合规认证

---

## 附录 A：与 ReAct 的关系

ReAct（Reason + Act）是一种控制流模式，但在生产场景有明显问题：

| ReAct 问题 | 本框架解决方案 |
|-----------|---------------|
| 每步都需要强模型决策 | Plan-Execute-Reflect 分层，执行用小模型 |
| 没有显式规划阶段 | Planner 先生成完整计划 |
| 容易陷入无效循环 | Done Validator 外部判定 |
| 小模型执行效果差 | 模型分层 + Skills 提供上下文 |
| 状态在 prompt 里传递 | Event Log 外化状态 |

**本框架不是"不用 ReAct"，而是"把 ReAct 的思想分层实现"。**

---

## 附录 B：术语表

| 术语 | 定义 |
|------|------|
| Event Log | Append-only 的事件日志，是系统状态的唯一真相来源 |
| Tool Runtime | 工具执行运行时，负责权限、幂等、补偿等合同执行 |
| Done Validator | 外部可验证的完成判定器 |
| Policy Engine | 安全与数据治理的总开关 |
| Skill | 领域知识包，包含 SKILL.md + 引用文档 + 脚本 |
| Decision Record | 结构化的决策记录，短、可审计、不存敏感原文 |
| PER Loop | Plan-Execute-Reflect 循环，本框架的核心编排模式 |

---

*文档版本: 2.0*
*最后更新: 基于多轮技术评审*
*状态: 可进入架构评审*
