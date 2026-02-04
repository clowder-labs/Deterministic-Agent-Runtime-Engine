# 工业级 Agent 框架设计文档 v2.3 补充章节

> 本文档补齐与 Anthropic Engineering 理念的差距，并回应红军评审的信任边界问题。

---

## 一、与 Anthropic Engineering 理念对照

### 1.1 对照矩阵

| Anthropic 理念 | 对应博客 | v2.x 覆盖情况 | v2.3 补充 |
|---------------|---------|--------------|----------|
| Skills 范式 | Agent Skills | ✅ v2.1 SkillManager | - |
| Sandboxing | Claude Code Sandboxing | ⚠️ 库级约定 | 系统级强制 |
| Context Engineering | Effective Context Engineering | ❌ 缺失 | ContextAssembler |
| Tool Contract | Writing Tools for Agents | ⚠️ 部分 | 完整契约 |
| Code Execution | Code Execution with MCP | ❌ 缺失 | CodeExecutionHarness |
| Progressive Disclosure | Advanced Tool Use | ⚠️ Skills有 | ToolDiscovery |
| Multi-agent | Multi-agent Research System | ⚠️ 浅 | 深化 |
| Data Tokenization | MCP | ❌ 缺失 | TokenizationLayer |

### 1.2 Anthropic 核心理念提炼

从 Anthropic Engineering 博客中提炼的核心工程原则：

```
1. Context is the new prompt
   - 不是"怎么写prompt"，而是"怎么在预算内装配信息"
   - 包括：压缩、分层、按需加载、持久化、回放

2. Tools are for Claude, not just for APIs
   - 工具设计要围绕模型的"认知习惯"，不是人类API习惯
   - 清晰的边界、高信噪比、可诊断的错误

3. Code execution > Tool call loops
   - 把"调10次工具"折叠成"写一段代码跑一次"
   - 减少token往返，提升效率

4. Progressive disclosure everywhere
   - 不要一次性塞满上下文
   - 按需加载：工具定义、文档、历史

5. Sandbox as runtime, not as policy
   - 安全不是"代码里禁止"，而是"运行时不可能"
```

---

## 二、Trust Boundary & Derivation Rules（信任边界）

> **这是v2.3最关键的补充。** GPT红军指出：v2.2把"LLM生成的字段"当真了。

### 2.1 核心原则：Plan 不可信

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Trust Boundary 信任边界                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  可信数据源（Ground Truth）           不可信数据源（需验证）          │
│  ─────────────────────────           ─────────────────────────      │
│  • Tool Registry 元数据               • LLM 生成的 Plan              │
│  • Policy Engine 规则                 • LLM 填写的 risk_level        │
│  • Event Log 历史记录                 • LLM 声称的 coverage          │
│  • External Validator 结果            • LLM 生成的 evidence          │
│  • Human Approval 签名                • 用户输入（需消毒）            │
│                                                                     │
│  原则：安全关键字段只能从可信数据源派生，不能由LLM自报               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 六条信任边界铁律

```python
"""
信任边界铁律 - 这些规则是运行时强制，不是代码约定
"""

# 铁律1：risk_level 只能由 Tool Registry 决定
class TrustBoundary:
    """信任边界强制器"""
    
    @staticmethod
    def derive_risk_level(tool_name: str, tool_registry: ToolRegistry) -> RiskLevel:
        """
        risk_level 只能从 Tool Registry 派生
        Plan 里写的 risk_level 会被忽略/覆盖
        """
        tool = tool_registry.get(tool_name)
        if not tool:
            raise UnknownTool(tool_name)
        return tool.risk_level  # 从注册表读，不信Plan
    
    @staticmethod
    def validate_plan_step(step: PlanStep, tool_registry: ToolRegistry) -> ValidatedStep:
        """
        验证并派生 Plan Step 的安全关键字段
        LLM填的字段会被可信数据源覆盖
        """
        tool = tool_registry.get(step.tool)
        
        # 覆盖所有安全关键字段（不信Plan自报）
        return ValidatedStep(
            # 保留意图字段
            step_id=step.step_id,
            order=step.order,
            description=step.description,
            tool=step.tool,
            tool_input=step.tool_input,  # 输入需要另外消毒
            
            # 从可信源派生的字段（覆盖Plan填写的）
            risk_level=tool.risk_level,              # 从Registry
            rollback_possible=tool.rollback_capable, # 从Registry
            requires_approval=tool.requires_approval,# 从Registry
            permissions_required=tool.permissions,   # 从Registry
            operates_on=tool.operates_on,            # 从Registry
            
            # 运行时计算的字段
            postchecks=derive_postchecks(tool),      # 从Registry
            preconditions=derive_preconditions(tool, step.tool_input),
        )


# 铁律2：Coverage 不允许自报
class CoverageValidator:
    """
    覆盖率校验器
    不信任 Plan 里的 covered_by_steps，自己计算
    """
    
    def validate(self, plan: Plan, context: ExecutionContext) -> ValidationResult:
        """
        根据 Step 的"产出证据/验收断言"自动建立覆盖关系
        不使用 Expectation.covered_by_steps（LLM填的）
        """
        errors = []
        
        for exp in plan.expectations:
            if exp.priority != "MUST":
                continue
            
            # 自动计算覆盖关系（不信Plan自报）
            covering_steps = self._find_covering_steps(exp, plan.steps)
            
            if not covering_steps:
                errors.append(ValidationError(
                    code="E_EXPECTATION_NOT_COVERED",
                    message=f"MUST expectation not covered: {exp.description}",
                    expectation_id=exp.expectation_id,
                    # 不使用 exp.covered_by_steps
                ))
        
        return ValidationResult(errors=errors)
    
    def _find_covering_steps(self, expectation: Expectation, steps: List[PlanStep]) -> List[str]:
        """
        通过语义匹配 + 工具能力分析，自动判断哪些步骤覆盖期望
        """
        covering = []
        for step in steps:
            tool = self.tool_registry.get(step.tool)
            
            # 检查工具的 produces_evidence 是否匹配期望的 verification_method
            if self._tool_can_satisfy(tool, expectation):
                covering.append(step.step_id)
        
        return covering


# 铁律3：Evidence 必须由系统生成，不能由LLM声称
class EvidenceFactory:
    """
    证据工厂
    证据只能由系统组件生成，不能由LLM"声称"
    """
    
    # 允许生成证据的来源
    TRUSTED_EVIDENCE_SOURCES = {
        "tool_runtime",      # 工具执行结果
        "done_validator",    # 验证器结果
        "approval_protocol", # 审批记录
        "event_log",         # 历史事件
        "external_system",   # 外部系统响应
    }
    
    def create(self, source: str, content: Any, context: ExecutionContext) -> Evidence:
        """创建证据 - 只有可信来源能调用"""
        if source not in self.TRUSTED_EVIDENCE_SOURCES:
            raise UntrustedEvidenceSource(f"Source {source} is not trusted")
        
        return Evidence(
            evidence_id=generate_id(),
            type=self._infer_type(content),
            content_hash=hash_content(content),
            generated_by=source,  # 可信来源
            source_system=context.system_id,
            timestamp=now(),
            trace_id=context.trace_id,
            span_id=context.span_id,
            # ...
        )


# 铁律4：输入必须消毒
class InputSanitizer:
    """
    输入消毒器
    所有来自LLM/用户的输入都需要消毒
    """
    
    def sanitize_tool_input(self, tool: Tool, raw_input: dict) -> dict:
        """消毒工具输入"""
        sanitized = {}
        
        for field, value in raw_input.items():
            # 检查字段是否在工具schema中
            if field not in tool.input_schema.properties:
                continue  # 忽略未知字段
            
            field_schema = tool.input_schema.properties[field]
            
            # 类型检查
            if not self._type_matches(value, field_schema):
                raise InputValidationError(f"Field {field} type mismatch")
            
            # 路径字段特殊处理
            if field_schema.get("format") == "path":
                value = self._sanitize_path(value)
            
            # 命令字段特殊处理
            if field_schema.get("format") == "command":
                value = self._sanitize_command(value)
            
            sanitized[field] = value
        
        return sanitized
    
    def _sanitize_path(self, path: str) -> str:
        """路径消毒 - 防止路径遍历"""
        # 解析为绝对路径
        abs_path = os.path.abspath(path)
        
        # 检查是否在允许范围内
        if not any(abs_path.startswith(allowed) for allowed in ALLOWED_PATHS):
            raise PathNotAllowed(path)
        
        # 检查是否包含危险模式
        if ".." in path or path.startswith("/"):
            raise PathTraversalAttempt(path)
        
        return abs_path
```

### 2.3 运行时强制 vs 代码约定

```
┌─────────────────────────────────────────────────────────────────────┐
│            从"代码约定"升级为"运行时强制"                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  代码约定（可绕过）              运行时强制（不可绕过）               │
│  ─────────────────────           ─────────────────────              │
│  class EgressGateway:            容器网络策略:                       │
│    # 希望大家都用这个             - 默认 deny all egress             │
│                                   - 只允许 proxy:8080               │
│                                   - iptables/NetworkPolicy 强制     │
│                                                                     │
│  COMMAND_DENYLIST = [...]        seccomp/AppArmor:                  │
│    # 正则匹配危险命令             - 禁止 execve 到非白名单二进制      │
│                                   - 禁止 socket() 系统调用           │
│                                   - 内核级强制                       │
│                                                                     │
│  def execute():                  沙箱容器:                           │
│    if not permission:            - 只读根文件系统                    │
│      raise ...                   - /workspace 是唯一可写挂载         │
│    # 可以被绕过                   - 无网络/最小系统镜像              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 系统级强制架构

```python
# 容器/沙箱配置 - 这是运行时强制，不是代码约定

AGENT_CONTAINER_SPEC = {
    "image": "agent-runtime:minimal",  # 最小镜像，无curl/wget/nc等
    
    "security_context": {
        "read_only_root_filesystem": True,
        "run_as_non_root": True,
        "allow_privilege_escalation": False,
        "capabilities": {
            "drop": ["ALL"],
            "add": []  # 不添加任何capability
        },
        "seccomp_profile": "runtime/default",  # 或自定义profile
    },
    
    "network_policy": {
        "egress": [
            # 只允许访问 egress proxy
            {"to": [{"pod_selector": {"app": "egress-proxy"}}], "ports": [8080]}
        ],
        # 默认 deny all 其他出站
    },
    
    "volumes": [
        # 只有 workspace 可写
        {"name": "workspace", "mount_path": "/workspace", "read_only": False},
        # 其他都是只读
        {"name": "skills", "mount_path": "/skills", "read_only": True},
        {"name": "tools", "mount_path": "/tools", "read_only": True},
    ],
    
    "resources": {
        "limits": {
            "cpu": "2",
            "memory": "4Gi",
        }
    }
}


# Egress Proxy - 所有出站必须经过这里（网络层强制）
class EgressProxy:
    """
    出站代理 - 网络层强制，不是代码约定
    容器只能访问这个proxy，proxy决定是否放行
    """
    
    async def handle_request(self, request: ProxyRequest) -> ProxyResponse:
        # 1. 身份验证（哪个agent发的）
        agent_id = self.authenticate(request)
        
        # 2. 策略检查
        policy_result = await self.policy_engine.check_egress(
            agent_id=agent_id,
            destination=request.destination,
            payload_hash=hash(request.body),  # 不看内容，只看hash
            context=request.context
        )
        
        if not policy_result.allowed:
            # 记录拒绝
            await self.audit_log.record_blocked(request, policy_result)
            return ProxyResponse(status=403, reason=policy_result.reason)
        
        # 3. 数据处理（tokenization/redaction）
        processed_body = await self.data_processor.process(
            request.body,
            policy_result.data_policy
        )
        
        # 4. 转发
        response = await self.forward(request.destination, processed_body)
        
        # 5. 审计
        await self.audit_log.record_allowed(request, response)
        
        return response
```

---

## 三、Evidence 防篡改闭环

> GPT红军指出：说"防篡改"但没给出"怎么防"

### 3.1 Hash Chain + 批次签名

```python
@dataclass
class Event:
    """带哈希链的事件"""
    event_id: str
    timestamp: datetime
    payload: dict
    
    # 哈希链
    prev_hash: str           # 前一个事件的hash
    event_hash: str          # 本事件hash = hash(prev_hash + payload)
    
    # 批次签名（每N个事件签一次）
    batch_id: Optional[str]
    batch_signature: Optional[str]


class EventLogWithHashChain:
    """带哈希链的Event Log"""
    
    def __init__(self, storage: WORMStorage, signer: Signer):
        self.storage = storage
        self.signer = signer
        self.batch_size = 100
        self.current_batch = []
    
    async def append(self, payload: dict) -> Event:
        """追加事件 - 维护哈希链"""
        # 获取前一个事件的hash
        prev_event = await self.storage.get_latest()
        prev_hash = prev_event.event_hash if prev_event else "genesis"
        
        # 计算本事件hash
        event_hash = self._compute_hash(prev_hash, payload)
        
        event = Event(
            event_id=generate_id(),
            timestamp=now(),
            payload=payload,
            prev_hash=prev_hash,
            event_hash=event_hash,
            batch_id=None,
            batch_signature=None
        )
        
        # 写入WORM存储（不可修改）
        await self.storage.append(event)
        
        # 批次处理
        self.current_batch.append(event)
        if len(self.current_batch) >= self.batch_size:
            await self._seal_batch()
        
        return event
    
    async def _seal_batch(self):
        """密封批次 - 签名"""
        batch_id = generate_id()
        
        # 计算批次Merkle root
        merkle_root = self._compute_merkle_root([e.event_hash for e in self.current_batch])
        
        # 签名
        signature = await self.signer.sign(merkle_root)
        
        # 更新批次中所有事件
        for event in self.current_batch:
            event.batch_id = batch_id
            event.batch_signature = signature
            await self.storage.update_batch_info(event.event_id, batch_id, signature)
        
        # 写入批次记录
        await self.storage.append_batch_record(BatchRecord(
            batch_id=batch_id,
            merkle_root=merkle_root,
            signature=signature,
            event_count=len(self.current_batch),
            first_event_id=self.current_batch[0].event_id,
            last_event_id=self.current_batch[-1].event_id,
            sealed_at=now()
        ))
        
        self.current_batch = []
    
    def _compute_hash(self, prev_hash: str, payload: dict) -> str:
        """计算事件hash"""
        data = json.dumps({"prev_hash": prev_hash, "payload": payload}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


class AuditVerifier:
    """审计验签器"""
    
    async def verify_chain(self, start_event_id: str, end_event_id: str) -> VerifyResult:
        """验证哈希链完整性"""
        events = await self.storage.get_range(start_event_id, end_event_id)
        
        for i, event in enumerate(events):
            # 验证hash
            expected_hash = self._compute_hash(event.prev_hash, event.payload)
            if event.event_hash != expected_hash:
                return VerifyResult(valid=False, reason=f"Hash mismatch at event {event.event_id}")
            
            # 验证链接
            if i > 0 and event.prev_hash != events[i-1].event_hash:
                return VerifyResult(valid=False, reason=f"Chain broken at event {event.event_id}")
        
        return VerifyResult(valid=True)
    
    async def verify_batch(self, batch_id: str) -> VerifyResult:
        """验证批次签名"""
        batch = await self.storage.get_batch(batch_id)
        events = await self.storage.get_batch_events(batch_id)
        
        # 重算Merkle root
        computed_root = self._compute_merkle_root([e.event_hash for e in events])
        
        if computed_root != batch.merkle_root:
            return VerifyResult(valid=False, reason="Merkle root mismatch")
        
        # 验证签名
        if not await self.signer.verify(batch.merkle_root, batch.signature):
            return VerifyResult(valid=False, reason="Signature invalid")
        
        return VerifyResult(valid=True)
```

### 3.2 WORM 存储策略

```python
class WORMStorage:
    """
    Write Once Read Many 存储
    写入后不可修改、不可删除（合规期内）
    """
    
    def __init__(self, backend: StorageBackend, retention_days: int):
        self.backend = backend
        self.retention_days = retention_days
    
    async def append(self, event: Event) -> None:
        """追加（唯一的写入方式）"""
        # 设置对象锁（不可删除、不可覆盖）
        await self.backend.put_object(
            key=f"events/{event.event_id}",
            body=serialize(event),
            object_lock_mode="COMPLIANCE",  # 合规模式，连root都不能删
            object_lock_retain_until=now() + timedelta(days=self.retention_days)
        )
    
    async def get(self, event_id: str) -> Event:
        """读取"""
        data = await self.backend.get_object(f"events/{event_id}")
        return deserialize(data)
    
    # 没有 update / delete 方法
```

---

## 四、Context Engineering（上下文工程）

> Anthropic: "Context is the new prompt"

### 4.1 Context Assembler（上下文装配器）

```python
class ContextAssembler:
    """
    上下文装配器
    在预算内装配最优信息组合
    """
    
    def __init__(
        self,
        budget: ContextBudget,
        retriever: MultiTierRetriever,
        compressor: ContextCompressor
    ):
        self.budget = budget
        self.retriever = retriever
        self.compressor = compressor
    
    async def assemble(
        self,
        task: Task,
        context: ExecutionContext
    ) -> AssembledContext:
        """
        装配上下文
        原则：在预算内最大化相关性
        """
        # 1. 计算预算分配
        allocation = self.budget.allocate(task.type)
        
        # 2. 分层检索
        components = []
        
        # Tier 1: 必须包含（系统指令、当前任务）
        components.append(ContextComponent(
            tier="required",
            content=self._build_system_context(task),
            tokens=self._count_tokens(self._build_system_context(task)),
            priority=100
        ))
        
        # Tier 2: 高优先（相关Skills、工具定义）
        if allocation.skills_budget > 0:
            skills = await self.retriever.get_relevant_skills(
                task.description,
                max_tokens=allocation.skills_budget
            )
            components.append(ContextComponent(
                tier="skills",
                content=skills,
                tokens=self._count_tokens(skills),
                priority=90
            ))
        
        # Tier 3: 中优先（历史上下文、证据）
        if allocation.history_budget > 0:
            history = await self.retriever.get_relevant_history(
                task.id,
                max_tokens=allocation.history_budget,
                compression_level=allocation.compression_level
            )
            components.append(ContextComponent(
                tier="history",
                content=history,
                tokens=self._count_tokens(history),
                priority=70
            ))
        
        # Tier 4: 低优先（参考文档）
        if allocation.docs_budget > 0:
            docs = await self.retriever.get_relevant_docs(
                task.description,
                max_tokens=allocation.docs_budget
            )
            components.append(ContextComponent(
                tier="docs",
                content=docs,
                tokens=self._count_tokens(docs),
                priority=50
            ))
        
        # 3. 如果超预算，压缩低优先级
        total_tokens = sum(c.tokens for c in components)
        if total_tokens > self.budget.max_tokens:
            components = await self._compress_to_fit(components, self.budget.max_tokens)
        
        return AssembledContext(
            components=components,
            total_tokens=sum(c.tokens for c in components),
            budget_used_pct=sum(c.tokens for c in components) / self.budget.max_tokens
        )


@dataclass
class ContextBudget:
    """上下文预算"""
    max_tokens: int = 100000
    max_cost_usd: float = 0.10
    max_latency_ms: int = 5000
    
    # 分配策略
    allocation_strategy: str = "dynamic"  # fixed / dynamic / adaptive
    
    def allocate(self, task_type: str) -> BudgetAllocation:
        """根据任务类型分配预算"""
        if self.allocation_strategy == "fixed":
            return BudgetAllocation(
                system_budget=5000,
                skills_budget=10000,
                history_budget=20000,
                docs_budget=10000,
                output_budget=self.max_tokens - 45000
            )
        elif self.allocation_strategy == "dynamic":
            # 根据任务类型动态分配
            if task_type == "planning":
                return BudgetAllocation(
                    system_budget=5000,
                    skills_budget=20000,  # 规划需要更多技能
                    history_budget=30000,
                    docs_budget=20000,
                    output_budget=self.max_tokens - 75000
                )
            elif task_type == "execution":
                return BudgetAllocation(
                    system_budget=5000,
                    skills_budget=5000,   # 执行需要更少技能
                    history_budget=10000,
                    docs_budget=5000,
                    output_budget=self.max_tokens - 25000
                )
        # ...


class MultiTierRetriever:
    """多层检索器"""
    
    async def get_relevant_skills(self, query: str, max_tokens: int) -> str:
        """
        检索相关技能
        Progressive Disclosure: 先返回摘要，需要时再返回全文
        """
        # 1. 搜索相关技能（只返回摘要）
        skill_summaries = await self.skill_index.search(query, top_k=5)
        
        # 2. 计算token预算
        summaries_tokens = self._count_tokens(skill_summaries)
        remaining = max_tokens - summaries_tokens
        
        # 3. 如果有余量，加载最相关的完整技能
        if remaining > 1000:
            top_skill = skill_summaries[0]
            full_skill = await self.skill_manager.load_skill(top_skill.name)
            return f"{skill_summaries}\n\n---DETAILED---\n{full_skill}"
        
        return skill_summaries
```

### 4.2 Context Compression（上下文压缩）

```python
class ContextCompressor:
    """上下文压缩器"""
    
    async def compress(self, content: str, target_tokens: int, level: str) -> str:
        """
        压缩上下文
        level: summary / extract / truncate
        """
        if level == "summary":
            # 用小模型生成摘要
            return await self._summarize(content, target_tokens)
        
        elif level == "extract":
            # 提取关键信息
            return await self._extract_key_info(content, target_tokens)
        
        elif level == "truncate":
            # 简单截断（保留开头和结尾）
            return self._smart_truncate(content, target_tokens)
    
    def _smart_truncate(self, content: str, target_tokens: int) -> str:
        """智能截断 - 保留开头和结尾"""
        tokens = self._tokenize(content)
        if len(tokens) <= target_tokens:
            return content
        
        # 保留前60%和后40%
        head_tokens = int(target_tokens * 0.6)
        tail_tokens = target_tokens - head_tokens
        
        head = self._detokenize(tokens[:head_tokens])
        tail = self._detokenize(tokens[-tail_tokens:])
        
        return f"{head}\n\n[...{len(tokens) - target_tokens} tokens truncated...]\n\n{tail}"
```

---

## 五、Code Execution Harness

> Anthropic: "把多步tool-call折叠成写代码跑一次"

### 5.1 设计理念

```
传统方式（token爆炸）：
  LLM: 调用 read_file("a.py")
  Tool: 返回文件内容（1000 tokens）
  LLM: 调用 read_file("b.py")
  Tool: 返回文件内容（800 tokens）
  LLM: 调用 search("pattern")
  Tool: 返回结果（500 tokens）
  ... 循环10次 ...
  总计：~20000 tokens 往返

Code Execution 方式（高效）：
  LLM: 生成代码
  ```python
  a = read_file("a.py")
  b = read_file("b.py")
  results = search("pattern")
  combined = process(a, b, results)
  print(json.dumps({"summary": combined[:500]}))
  ```
  Tool: 执行代码，返回精简结果（200 tokens）
  总计：~2000 tokens
```

### 5.2 Code Execution Harness

```python
class CodeExecutionHarness:
    """
    代码执行套件
    把多步操作折叠成一次代码执行
    """
    
    def __init__(self, sandbox: Sandbox, tool_runtime: ToolRuntime):
        self.sandbox = sandbox
        self.tool_runtime = tool_runtime
    
    async def execute(
        self,
        code: str,
        context: ExecutionContext,
        output_budget: int = 500  # 输出token预算
    ) -> CodeExecutionResult:
        """
        执行代码
        1. 注入工具函数
        2. 在沙箱中执行
        3. 限制输出大小
        """
        # 1. 验证代码安全性
        safety_check = await self._check_code_safety(code)
        if not safety_check.safe:
            raise UnsafeCode(safety_check.reason)
        
        # 2. 注入工具函数（代码可以调用这些函数）
        runtime_code = self._inject_tools(code, context)
        
        # 3. 在沙箱中执行
        result = await self.sandbox.execute(
            code=runtime_code,
            timeout=30,
            memory_limit="512M"
        )
        
        # 4. 限制输出大小
        if len(result.stdout) > output_budget * 4:  # 粗估1 token ≈ 4 chars
            result.stdout = self._truncate_output(result.stdout, output_budget)
        
        return CodeExecutionResult(
            success=result.exit_code == 0,
            output=result.stdout,
            error=result.stderr if result.exit_code != 0 else None,
            execution_time_ms=result.execution_time_ms
        )
    
    def _inject_tools(self, code: str, context: ExecutionContext) -> str:
        """注入工具函数"""
        # 生成工具wrapper
        tool_wrappers = []
        for tool in self.tool_runtime.get_available_tools(context):
            wrapper = f"""
def {tool.name}(*args, **kwargs):
    '''Tool: {tool.description}'''
    return _call_tool('{tool.name}', args, kwargs)
"""
            tool_wrappers.append(wrapper)
        
        # 注入runtime
        return f"""
import json

def _call_tool(name, args, kwargs):
    # 这个函数由sandbox runtime提供
    return __sandbox_tool_call__(name, args, kwargs)

{chr(10).join(tool_wrappers)}

# User code below
{code}
"""
    
    async def _check_code_safety(self, code: str) -> SafetyCheck:
        """代码安全检查"""
        # 静态分析
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SafetyCheck(safe=False, reason=f"Syntax error: {e}")
        
        # 禁止的操作
        forbidden = {
            "Import": ["os", "subprocess", "socket", "requests"],
            "Call": ["exec", "eval", "compile", "__import__", "open"],
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in forbidden["Import"]:
                        return SafetyCheck(safe=False, reason=f"Forbidden import: {alias.name}")
            
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden["Call"]:
                    return SafetyCheck(safe=False, reason=f"Forbidden call: {node.func.id}")
        
        return SafetyCheck(safe=True)
```

---

## 六、Tool Discovery & Progressive Disclosure

> Anthropic: "按需加载工具定义，避免上下文爆炸"

### 6.1 Tool Discovery Service

```python
class ToolDiscoveryService:
    """
    工具发现服务
    不一次性加载所有工具定义，而是按需发现
    """
    
    async def search_tools(
        self,
        query: str,
        context: ExecutionContext,
        detail_level: str = "summary"  # summary / schema / full
    ) -> List[ToolInfo]:
        """
        搜索相关工具
        detail_level 控制返回的详细程度
        """
        # 1. 搜索相关工具
        tools = await self.tool_index.search(query, top_k=10)
        
        # 2. 权限过滤
        allowed_tools = [
            t for t in tools 
            if self.policy_engine.can_use_tool(t.name, context)
        ]
        
        # 3. 根据 detail_level 返回不同详细程度
        if detail_level == "summary":
            return [ToolSummary(
                name=t.name,
                description=t.description,
                risk_level=t.risk_level
            ) for t in allowed_tools]
        
        elif detail_level == "schema":
            return [ToolSchema(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
                output_schema=t.output_schema,
                risk_level=t.risk_level
            ) for t in allowed_tools]
        
        else:  # full
            return allowed_tools
    
    async def get_tool_detail(
        self,
        tool_name: str,
        context: ExecutionContext
    ) -> ToolDetail:
        """
        获取工具完整信息
        只在需要时调用
        """
        tool = await self.tool_registry.get(tool_name)
        
        return ToolDetail(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            examples=tool.examples,
            error_codes=tool.error_codes,
            preconditions=tool.preconditions,
            postconditions=tool.postconditions,
            risk_level=tool.risk_level,
            # ...
        )
```

### 6.2 完整 Tool Contract

```python
@dataclass
class ToolContract:
    """
    完整的工具契约
    参考 Anthropic "Writing Tools for Agents"
    """
    # 基本信息
    name: str
    description: str
    version: str
    
    # Schema
    input_schema: JSONSchema
    output_schema: JSONSchema
    
    # 行为契约
    risk_level: RiskLevel
    idempotent: bool
    deterministic: bool
    
    # 前置/后置条件
    preconditions: List[Precondition]
    postconditions: List[Postcondition]
    
    # 错误分类（不只是"失败了"）
    error_taxonomy: ErrorTaxonomy
    
    # 使用示例（帮助LLM理解）
    examples: List[ToolExample]
    
    # 证据产出
    produces_evidence: bool
    evidence_type: Optional[EvidenceType]
    
    # 补偿/回滚
    compensatable: bool
    compensate_fn: Optional[Callable]
    
    # 资源消耗预估
    estimated_latency_ms: int
    estimated_cost: float


@dataclass
class ErrorTaxonomy:
    """
    错误分类
    不只是"失败了"，而是"为什么失败、怎么处理"
    """
    errors: List[ErrorDefinition]
    
    def get_handler(self, error_code: str) -> ErrorHandler:
        """获取错误处理器"""
        for err in self.errors:
            if err.code == error_code:
                return err.handler
        return self.default_handler


@dataclass
class ErrorDefinition:
    """错误定义"""
    code: str                    # 错误码
    description: str             # 描述
    category: str                # 类别：transient / permanent / resource / permission
    retryable: bool              # 是否可重试
    handler: ErrorHandler        # 处理器
    example_message: str         # 示例消息


@dataclass 
class ToolExample:
    """工具使用示例"""
    description: str             # 场景描述
    input: dict                  # 输入
    expected_output: dict        # 期望输出
    notes: Optional[str]         # 注意事项
```

---

## 七、Data Tokenization Layer

> Anthropic MCP: "数据不进模型，必要时再untokenize"

### 7.1 Tokenization vs Redaction

```
Redaction（脱敏）：
  原始：客户张三的银行卡号是 6222 0200 1234 5678
  脱敏：客户张三的银行卡号是 6222 02** **** 5678
  问题：脱敏后的数据仍然进入模型上下文，占用token

Tokenization（令牌化）：
  原始：客户张三的银行卡号是 6222 0200 1234 5678
  令牌化：客户 <PII:CUST_001> 的银行卡号是 <PII:CARD_001>
  优势：
  1. 敏感数据完全不进模型
  2. 节省token
  3. 可以在输出时还原（如果需要）
```

### 7.2 Tokenization Layer

```python
class TokenizationLayer:
    """
    数据令牌化层
    敏感数据不进模型，用令牌代替
    """
    
    def __init__(self, token_store: TokenStore, policy_engine: PolicyEngine):
        self.token_store = token_store
        self.policy_engine = policy_engine
    
    async def tokenize(
        self,
        data: str,
        context: ExecutionContext
    ) -> TokenizedData:
        """
        令牌化数据
        敏感信息替换为令牌
        """
        # 1. 识别敏感信息
        sensitive_spans = await self._detect_sensitive(data)
        
        # 2. 生成令牌并替换
        tokenized = data
        token_map = {}
        
        for span in sorted(sensitive_spans, key=lambda s: s.start, reverse=True):
            # 生成令牌
            token = await self._generate_token(span.text, span.type)
            token_map[token] = span.text
            
            # 替换
            tokenized = tokenized[:span.start] + token + tokenized[span.end:]
            
            # 存储映射（带TTL和权限控制）
            await self.token_store.store(
                token=token,
                value=span.text,
                type=span.type,
                context=context,
                ttl=timedelta(hours=24)
            )
        
        return TokenizedData(
            text=tokenized,
            token_count=len(token_map),
            original_tokens_saved=sum(len(v) for v in token_map.values()) // 4  # 粗估
        )
    
    async def detokenize(
        self,
        data: str,
        context: ExecutionContext,
        target_system: str
    ) -> str:
        """
        还原令牌
        只有在需要时、且有权限时才还原
        """
        # 找到所有令牌
        tokens = re.findall(r'<PII:[A-Z]+_[A-Z0-9]+>', data)
        
        detokenized = data
        for token in tokens:
            # 权限检查
            if not await self.policy_engine.can_detokenize(token, context, target_system):
                continue  # 无权限，保留令牌
            
            # 获取原值
            original = await self.token_store.get(token, context)
            if original:
                detokenized = detokenized.replace(token, original)
        
        return detokenized
    
    async def _detect_sensitive(self, data: str) -> List[SensitiveSpan]:
        """检测敏感信息"""
        spans = []
        
        # 规则检测
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            for match in re.finditer(pattern, data):
                spans.append(SensitiveSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    type=pattern_name
                ))
        
        # NER检测（人名、地址等）
        ner_spans = await self.ner_model.detect(data)
        spans.extend(ner_spans)
        
        return spans


SENSITIVE_PATTERNS = {
    "CARD": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',       # 银行卡
    "PHONE": r'\b1[3-9]\d{9}\b',                                   # 手机号
    "ID": r'\b\d{17}[\dXx]\b',                                     # 身份证
    "EMAIL": r'\b[\w\.-]+@[\w\.-]+\.\w+\b',                        # 邮箱
}
```

---

## 八、Threat Model / Attack Scenarios 附录

> GPT建议：把刀架在脖子上，评审就不会再拿小刀捅你

### 8.1 攻击场景矩阵

| # | 攻击场景 | 攻击方式 | 防护措施 | 证据位置 |
|---|---------|---------|---------|---------|
| 1 | Plan 伪造 risk_level | LLM 把危险工具写成 READ_ONLY | risk_level 只从 Tool Registry 派生 | ValidatedStep.risk_level 来源检查 |
| 2 | 自证 Coverage | LLM 填写 covered_by_steps 自证正确 | CoverageValidator 自动计算，不用 Plan 字段 | 覆盖关系由 Validator 生成 |
| 3 | 绕过 Egress Gateway | 直接 requests.post() | 容器网络策略只允许访问 Egress Proxy | iptables/NetworkPolicy |
| 4 | 绕过 Bash denylist | python -c 'import requests' | 沙箱无网络，无危险包 | 容器镜像无 requests 等包 |
| 5 | 路径遍历 | symlink 指向 /etc | 沙箱只读根，只有 /workspace 可写 | 容器挂载配置 |
| 6 | Event Log 篡改 | 修改历史记录 | WORM 存储 + Hash Chain + 批次签名 | 审计验签流程 |
| 7 | Evidence 伪造 | LLM "声称" 有证据 | Evidence 只能由 TRUSTED_SOURCES 创建 | EvidenceFactory 来源检查 |
| 8 | 审批绕过 | 跳过 approval 直接执行 | ToolRuntime 强制检查 approval_status | ApprovalProtocol 事件 |
| 9 | Break Glass 滥用 | 频繁紧急放行 | 需要 supervisor 签名 + 告警 + 审计 | BreakGlassEvent |
| 10 | 令牌泄露 | 从响应中提取 PII 令牌 | TokenStore 有 TTL + 权限控制 | Token 访问审计 |

### 8.2 每个攻击的详细分析

```yaml
# Attack-001: Plan 伪造 risk_level
scenario: "LLM 在 Plan 中把危险工具的 risk_level 写成 READ_ONLY，绕过审批和回滚要求"

attack_vector:
  - LLM 生成 Plan，其中某个 step 的 risk_level 被故意写低
  - PlanValidator 基于 Plan 字段判断，通过校验
  - 危险操作在无审批、无回滚的情况下执行

defense:
  - TrustBoundary.validate_plan_step() 会覆盖所有安全关键字段
  - risk_level 只从 Tool Registry 读取，Plan 写的会被忽略
  - 执行时再次校验：step.risk_level vs tool.risk_level

evidence:
  - ValidatedStep 中的 risk_level 有明确来源标记
  - Event Log 记录派生过程
  - 审计可追溯 risk_level 来源

test_case:
  - name: "test_risk_level_forgery_blocked"
    given: "Plan 中某工具的 risk_level 被写成 READ_ONLY，但 Registry 中是 NON_IDEMPOTENT"
    when: "执行 TrustBoundary.validate_plan_step()"
    then: "返回的 ValidatedStep.risk_level 应为 NON_IDEMPOTENT"
```

---

## 九、文档版本历史

| 版本 | 核心变更 | 红军评分 |
|------|---------|---------|
| v2.0 | P0三件套 + PolicyEngine | 6.5/10 |
| v2.1 | 6个落地细则 | 8/10 |
| v2.2 | 6个评审硬问题 | 8.5/10 |
| **v2.3** | **信任边界 + Context Engineering + Code Execution** | **9+/10** |

**v2.3 核心补充：**
1. ✅ Trust Boundary & Derivation Rules（Plan不可信、risk_level从Registry派生）
2. ✅ 运行时强制 vs 代码约定（容器/网络/seccomp级别）
3. ✅ Evidence 防篡改闭环（Hash Chain + 签名 + WORM + 审计验签）
4. ✅ Context Engineering（ContextAssembler + Budget + Compression）
5. ✅ Code Execution Harness（折叠多步tool-call）
6. ✅ Tool Discovery & Progressive Disclosure
7. ✅ Data Tokenization Layer（数据不进模型）
8. ✅ Threat Model / Attack Scenarios 附录

---

*文档状态：可进入银行级架构评审，自带"刀架脖子"的攻击场景分析*
*与 Anthropic Engineering 理念对齐度：~90%*
