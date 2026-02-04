# 工业级 Agent 框架设计文档 v2.1 补充章节

> 本文档是 v2.0 的补充，针对架构评审中可能被问爆的6个关键细则。

---

## 补充章节 1：并行/多 Agent 模型

### 1.1 核心原则：默认单 Writer

```
┌─────────────────────────────────────────────────────────────┐
│  默认模型：Single Writer per Task                            │
│                                                             │
│  • 同一 Task 在任意时刻只有一个 Agent 拥有写权限              │
│  • 写权限通过 Task Lease 机制获取                            │
│  • Lease 有 TTL，超时自动释放                                │
│  • 其他 Agent 只能 Read 或等待                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Task Lease 机制

```python
@dataclass
class TaskLease:
    """任务租约"""
    task_id: str
    holder_agent_id: str
    acquired_at: datetime
    ttl_seconds: int
    lease_version: int  # 用于乐观锁


class LeaseManager:
    """租约管理器"""
    
    async def acquire(self, task_id: str, agent_id: str, ttl: int = 300) -> Optional[TaskLease]:
        """
        尝试获取租约
        - 如果无人持有：授予租约
        - 如果已被他人持有且未过期：返回 None
        - 如果已过期：抢占租约
        """
        async with self.lock:
            existing = await self.store.get(task_id)
            
            if existing and not self._is_expired(existing):
                if existing.holder_agent_id == agent_id:
                    # 续约
                    return await self._renew(existing, ttl)
                else:
                    # 被他人持有
                    return None
            
            # 可以获取
            lease = TaskLease(
                task_id=task_id,
                holder_agent_id=agent_id,
                acquired_at=now(),
                ttl_seconds=ttl,
                lease_version=(existing.lease_version + 1) if existing else 1
            )
            await self.store.put(lease)
            return lease
    
    async def release(self, lease: TaskLease) -> bool:
        """
        释放租约
        使用乐观锁防止释放被抢占的租约
        """
        async with self.lock:
            current = await self.store.get(lease.task_id)
            if current and current.lease_version == lease.lease_version:
                await self.store.delete(lease.task_id)
                return True
            return False  # 已被抢占，不操作
    
    async def heartbeat(self, lease: TaskLease) -> Optional[TaskLease]:
        """心跳续约，长任务必须定期调用"""
        return await self.acquire(lease.task_id, lease.holder_agent_id, lease.ttl_seconds)
```

### 1.3 并行范围限制

| 操作类型 | 是否允许并行 | 条件 |
|---------|-------------|------|
| Read-only 查询 | ✅ 允许 | 无限制 |
| 幂等写入 | ✅ 允许 | 不同资源可并行，同一资源串行 |
| 不可幂等副作用 | ❌ 禁止并行 | 必须单 writer + 人在回路 |
| 可补偿操作 | ⚠️ 有条件允许 | 需要 Saga 协调器 |

### 1.4 多 Agent 协作模式

```
模式 A：主从模式（推荐）
┌──────────────┐
│ Coordinator  │  ← 持有 Task Lease，负责分解和合并
│   Agent      │
└──────┬───────┘
       │ 分配子任务（只读/幂等）
       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Worker A    │  │  Worker B    │  │  Worker C    │
│ (read-only)  │  │ (read-only)  │  │ (idempotent) │
└──────────────┘  └──────────────┘  └──────────────┘

模式 B：接力模式
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Agent A    │ ──▶ │   Agent B    │ ──▶ │   Agent C    │
│  (Planner)   │     │  (Executor)  │     │  (Reviewer)  │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │                    │
        └───────────────────┴────────────────────┘
                    Lease 依次传递
```

### 1.5 冲突处理策略

```python
class ConflictStrategy(Enum):
    FAIL_FAST = "fail_fast"           # 检测到冲突立即失败
    LAST_WRITER_WINS = "lww"          # 最后写入者胜（需要向量时钟）
    MERGE_IF_POSSIBLE = "merge"       # 尝试自动合并（仅限特定数据结构）
    HUMAN_RESOLUTION = "human"        # 提交人工处理


# Event Log 写入时的冲突检测
class EventLog:
    async def append(self, event: Event, expected_parent: Optional[str] = None) -> AppendResult:
        """
        带乐观锁的写入
        expected_parent: 期望的因果父事件ID
        """
        async with self.write_lock:
            # 检查因果链
            if expected_parent:
                actual_latest = await self.get_latest_for_task(event.task_id)
                if actual_latest and actual_latest.event_id != expected_parent:
                    # 检测到并发写入
                    return AppendResult(
                        success=False,
                        conflict=True,
                        conflict_event=actual_latest
                    )
            
            await self._storage.append(event)
            return AppendResult(success=True)
```

---

## 补充章节 2：Event Schema 演进与回放兼容

### 2.1 Schema 版本控制

```python
# 每个事件类型有独立的 schema 版本
EVENT_SCHEMAS = {
    "tool_executed": {
        "v1": ToolExecutedV1Schema,  # 初始版本
        "v2": ToolExecutedV2Schema,  # 增加了 risk_level 字段
        "v3": ToolExecutedV3Schema,  # 重命名 output → result
    },
    "decision_recorded": {
        "v1": DecisionRecordedV1Schema,
        "v2": DecisionRecordedV2Schema,
    }
}

# 当前写入版本
CURRENT_SCHEMA_VERSIONS = {
    "tool_executed": "v3",
    "decision_recorded": "v2",
}
```

### 2.2 兼容性规则

| 变更类型 | 是否允许 | 处理方式 |
|---------|---------|---------|
| 新增可选字段 | ✅ 允许 | 旧事件回放时填默认值 |
| 新增必填字段 | ❌ 禁止 | 必须有迁移脚本 |
| 删除字段 | ⚠️ 有条件 | 标记 deprecated，保留3个版本 |
| 重命名字段 | ⚠️ 有条件 | 必须提供双向映射 |
| 修改字段类型 | ❌ 禁止 | 必须新建字段 |

### 2.3 Schema 迁移器

```python
class SchemaMigrator:
    """Schema 迁移器 - 支持向前和向后兼容"""
    
    def __init__(self):
        # 迁移函数注册表
        self.migrations = {}
    
    def register(self, event_type: str, from_version: str, to_version: str, 
                 migrate_fn: Callable[[dict], dict]):
        """注册迁移函数"""
        key = (event_type, from_version, to_version)
        self.migrations[key] = migrate_fn
    
    def migrate(self, event: dict, target_version: str) -> dict:
        """
        将事件迁移到目标版本
        支持跨版本迁移（自动链式调用）
        """
        event_type = event["event_type"]
        current_version = event.get("schema_version", "v1")
        
        if current_version == target_version:
            return event
        
        # 找到迁移路径
        path = self._find_migration_path(event_type, current_version, target_version)
        
        # 依次执行迁移
        result = event.copy()
        for from_v, to_v in path:
            migrate_fn = self.migrations[(event_type, from_v, to_v)]
            result = migrate_fn(result)
            result["schema_version"] = to_v
        
        return result


# 迁移函数示例
@migrator.register("tool_executed", "v2", "v3")
def migrate_tool_executed_v2_to_v3(event: dict) -> dict:
    """v2 → v3: 重命名 output → result"""
    event = event.copy()
    if "output" in event:
        event["result"] = event.pop("output")
    return event


@migrator.register("tool_executed", "v3", "v2")  # 向后兼容
def migrate_tool_executed_v3_to_v2(event: dict) -> dict:
    """v3 → v2: 重命名 result → output"""
    event = event.copy()
    if "result" in event:
        event["output"] = event.pop("result")
    return event
```

### 2.4 Snapshot 与归档策略

```python
class SnapshotManager:
    """快照管理器 - 解决事件无限增长问题"""
    
    SNAPSHOT_INTERVAL = 1000  # 每1000个事件创建快照
    RETENTION_DAYS = {
        "hot": 30,       # 热数据：30天内可直接回放
        "warm": 180,     # 温数据：180天内可从快照恢复
        "cold": 2555,    # 冷数据：7年归档（合规要求）
    }
    
    async def create_snapshot(self, task_id: str) -> Snapshot:
        """
        创建快照
        1. 聚合当前状态
        2. 记录最后事件ID
        3. 标记旧事件可归档
        """
        events = await self.event_log.get_all(task_id)
        state = self._replay_to_state(events)
        
        snapshot = Snapshot(
            snapshot_id=generate_id(),
            task_id=task_id,
            created_at=now(),
            last_event_id=events[-1].event_id if events else None,
            state=state,
            event_count=len(events),
            schema_version=CURRENT_SCHEMA_VERSIONS
        )
        
        await self.snapshot_store.save(snapshot)
        
        # 标记旧事件可归档（不立即删除）
        await self.event_log.mark_archivable(task_id, before=snapshot.last_event_id)
        
        return snapshot
    
    async def replay_from_snapshot(self, task_id: str) -> State:
        """
        从快照恢复 + 回放后续事件
        """
        snapshot = await self.snapshot_store.get_latest(task_id)
        
        if not snapshot:
            # 无快照，全量回放
            events = await self.event_log.get_all(task_id)
            return self._replay_to_state(events)
        
        # 从快照恢复
        state = snapshot.state
        
        # 回放快照之后的事件
        new_events = await self.event_log.get_after(task_id, snapshot.last_event_id)
        for event in new_events:
            # 迁移到当前schema版本
            migrated = self.migrator.migrate(event, CURRENT_SCHEMA_VERSIONS[event.event_type])
            state = self._apply_event(state, migrated)
        
        return state
```

### 2.5 Event Log 的 SoT 边界（重要修正）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         真相源边界定义                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Event Log 是：                                                     │
│  ✅ Agent Runtime 的"动作与决策真相源"（Action/Decision SoT）        │
│  ✅ "我们做过什么"的证据链                                          │
│  ✅ 可审计、可回放的执行历史                                         │
│                                                                     │
│  Event Log 不是：                                                   │
│  ❌ 业务事实的真相源（交易状态、账户余额、客户风险等级）              │
│  ❌ 核心账本系统的替代品                                            │
│  ❌ 外部系统状态的缓存                                               │
│                                                                     │
│  关联方式：                                                         │
│  Event Log 通过 correlation_id / external_ref 绑定外部业务 SoT       │
│  查询业务事实时，必须查询外部系统，不能只信 Event Log                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 补充章节 3：Data Egress Gateway（数据出站网关）

### 3.1 架构位置

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Agent Framework                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │ Event Log   │    │Tool Runtime │    │Egress Gateway│  ← 新增     │
│  │             │    │             │    │             │             │
│  │ 内部状态    │    │ 工具执行    │    │ 出站数据    │             │
│  │ 不出框架    │    │ 可能出站    │────▶│ 强制过滤    │             │
│  └─────────────┘    └─────────────┘    └──────┬──────┘             │
│                                               │                     │
└───────────────────────────────────────────────┼─────────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────┐
                    │                           │                   │
                    ▼                           ▼                   ▼
            ┌─────────────┐           ┌─────────────┐      ┌─────────────┐
            │ 外部 LLM    │           │ 外部工具    │      │ 外部系统    │
            │ (Claude等)  │           │ (API调用)   │      │ (银行核心)  │
            └─────────────┘           └─────────────┘      └─────────────┘
```

### 3.2 强制执行点

**原则：所有出站数据必须经过 Egress Gateway，禁止绕过。**

```python
class EgressGateway:
    """
    数据出站网关
    所有发往框架外部的数据必须经过此网关
    """
    
    def __init__(self, policy_engine: PolicyEngine, audit_log: AuditLog):
        self.policy_engine = policy_engine
        self.audit_log = audit_log
    
    async def send(
        self, 
        destination: EgressDestination,
        payload: Any,
        context: ExecutionContext
    ) -> EgressResult:
        """
        发送数据到外部
        
        destination 类型：
        - EXTERNAL_LLM: 外部模型API（数据可能出境）
        - DOMESTIC_LLM: 国产模型（数据不出境）
        - LOCAL_LLM: 本地部署模型（数据不出框架）
        - EXTERNAL_TOOL: 外部工具/API
        - CORE_SYSTEM: 银行核心系统
        """
        
        # 1. 数据分级
        classification = self.policy_engine.classify_data(payload, context)
        
        # 2. 检查出站规则
        allowed = self.policy_engine.check_egress_policy(
            classification=classification,
            destination=destination,
            context=context
        )
        
        if not allowed.permitted:
            await self.audit_log.record_blocked_egress(
                payload_hash=hash(payload),
                destination=destination,
                reason=allowed.reason,
                context=context
            )
            raise EgressBlocked(allowed.reason)
        
        # 3. 应用脱敏策略
        redacted_payload = self.policy_engine.apply_egress_redaction(
            payload=payload,
            classification=classification,
            destination=destination
        )
        
        # 4. 记录出站审计
        await self.audit_log.record_egress(
            original_hash=hash(payload),
            redacted_hash=hash(redacted_payload),
            destination=destination,
            classification=classification,
            context=context
        )
        
        # 5. 实际发送
        return await self._do_send(destination, redacted_payload)


class EgressPolicy:
    """出站策略矩阵"""
    
    # 数据分级 × 目的地 → 允许/脱敏规则
    POLICY_MATRIX = {
        # PUBLIC 数据：任何目的地都可以
        (DataClassification.PUBLIC, EgressDestination.EXTERNAL_LLM): 
            EgressRule(permitted=True, redaction=None),
        (DataClassification.PUBLIC, EgressDestination.EXTERNAL_TOOL): 
            EgressRule(permitted=True, redaction=None),
        
        # INTERNAL 数据：外部LLM需要脱敏
        (DataClassification.INTERNAL, EgressDestination.EXTERNAL_LLM): 
            EgressRule(permitted=True, redaction=RedactionLevel.STANDARD),
        (DataClassification.INTERNAL, EgressDestination.DOMESTIC_LLM): 
            EgressRule(permitted=True, redaction=None),
        (DataClassification.INTERNAL, EgressDestination.LOCAL_LLM): 
            EgressRule(permitted=True, redaction=None),
        
        # CONFIDENTIAL 数据：只能发本地或国产，外部禁止
        (DataClassification.CONFIDENTIAL, EgressDestination.EXTERNAL_LLM): 
            EgressRule(permitted=False, reason="CONFIDENTIAL data cannot be sent to external LLM"),
        (DataClassification.CONFIDENTIAL, EgressDestination.DOMESTIC_LLM): 
            EgressRule(permitted=True, redaction=RedactionLevel.STRICT),
        (DataClassification.CONFIDENTIAL, EgressDestination.LOCAL_LLM): 
            EgressRule(permitted=True, redaction=RedactionLevel.STANDARD),
        
        # RESTRICTED 数据：只能本地，且需要审批
        (DataClassification.RESTRICTED, EgressDestination.LOCAL_LLM): 
            EgressRule(permitted=True, redaction=RedactionLevel.STRICT, requires_approval=True),
        # 其他目的地全部禁止
    }
```

### 3.3 Model Router 集成

```python
class ModelRouter:
    """模型路由器 - 必须通过 Egress Gateway"""
    
    def __init__(self, egress_gateway: EgressGateway, ...):
        self.egress_gateway = egress_gateway
    
    async def call(self, prompt: str, context: ExecutionContext) -> LLMResponse:
        # 选择模型
        model = self.select_model(...)
        destination = self._get_destination(model)
        
        # 所有LLM调用必须走 Egress Gateway
        # 不能直接调用 litellm.completion()
        result = await self.egress_gateway.send(
            destination=destination,
            payload={"prompt": prompt, "model": model},
            context=context
        )
        
        return result
```

---

## 补充章节 4：Tool 合同落地清单

### 4.1 各风险级别的必须字段

```yaml
# READ_ONLY 工具合同
read_only_contract:
  required:
    - name: string                    # 工具名称
    - description: string             # 描述
    - permission_scope: string        # 所需权限
    - timeout_seconds: int            # 超时时间
    - output_schema: JSONSchema       # 输出结构
    - retry_policy:                   # 重试策略
        max_retries: int
        backoff_type: "exponential" | "linear"
  optional:
    - cache_ttl_seconds: int          # 缓存时间
  forbidden:
    - compensate_fn                   # 只读不需要补偿
  
# IDEMPOTENT_WRITE 工具合同
idempotent_write_contract:
  required:
    - <<: *read_only_required         # 继承只读的必填项
    - idempotency_key_fn: Callable    # 幂等键生成函数
    - idempotent_window_seconds: int  # 幂等窗口
  optional:
    - compensate_fn: Callable         # 补偿函数（可选）
  test_requirements:
    - 连续调用两次，结果相同
    - 幂等键相同时不重复执行

# NON_IDEMPOTENT_EFFECT 工具合同
non_idempotent_contract:
  required:
    - <<: *read_only_required
    - dry_run_fn: Callable            # 预演函数
    - human_approval_required: bool   # 是否需要人工审批
    - side_effect_description: string # 副作用描述
    - reversible: bool                # 是否可逆
  forbidden:
    - retry_policy.max_retries > 0    # 禁止自动重试
  test_requirements:
    - dry_run 不产生副作用
    - 人工审批流程可用

# COMPENSATABLE 工具合同
compensatable_contract:
  required:
    - <<: *idempotent_write_required
    - compensate_fn: Callable         # 补偿函数（必须）
    - compensation_timeout: int       # 补偿超时
    - saga_participant: bool          # 是否参与Saga
  test_requirements:
    - 执行后可补偿
    - 补偿是幂等的
```

### 4.2 工具注册检查清单

```python
class ToolRegistrationChecker:
    """工具注册检查器"""
    
    def check(self, tool: Tool) -> CheckResult:
        errors = []
        warnings = []
        
        contract = TOOL_CONTRACTS[tool.risk_level]
        
        # 检查必填字段
        for field in contract["required"]:
            if not hasattr(tool, field) or getattr(tool, field) is None:
                errors.append(f"Missing required field: {field}")
        
        # 检查禁止字段
        for field in contract.get("forbidden", []):
            if hasattr(tool, field) and getattr(tool, field) is not None:
                errors.append(f"Forbidden field present: {field}")
        
        # 风险级别特定检查
        if tool.risk_level == RiskLevel.IDEMPOTENT_WRITE:
            # 检查幂等键函数签名
            if not self._check_idempotency_fn_signature(tool.idempotency_key_fn):
                errors.append("idempotency_key_fn must accept (input: dict) -> str")
        
        if tool.risk_level == RiskLevel.NON_IDEMPOTENT_EFFECT:
            # 检查重试策略
            if tool.retry_policy and tool.retry_policy.max_retries > 0:
                errors.append("NON_IDEMPOTENT tools cannot have auto-retry")
        
        if tool.risk_level == RiskLevel.COMPENSATABLE:
            # 检查补偿函数
            if not self._check_compensate_fn_signature(tool.compensate_fn):
                errors.append("compensate_fn must accept (original_input, original_output) -> bool")
        
        return CheckResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

### 4.3 测试用例模板

```python
# tests/tools/test_tool_contract.py

class ToolContractTestBase:
    """工具合同测试基类"""
    
    def test_required_fields_present(self):
        """检查必填字段"""
        contract = TOOL_CONTRACTS[self.tool.risk_level]
        for field in contract["required"]:
            assert hasattr(self.tool, field), f"Missing: {field}"
            assert getattr(self.tool, field) is not None, f"None: {field}"
    
    def test_timeout_reasonable(self):
        """超时设置合理"""
        assert 1 <= self.tool.timeout_seconds <= 300
    
    def test_output_schema_valid(self):
        """输出schema有效"""
        # 用测试输入调用，验证输出符合schema
        output = self.tool.execute(self.test_input)
        validate(output, self.tool.output_schema)


class IdempotentToolTestMixin:
    """幂等工具测试混入"""
    
    def test_idempotency_same_input_same_key(self):
        """相同输入产生相同幂等键"""
        key1 = self.tool.idempotency_key_fn(self.test_input)
        key2 = self.tool.idempotency_key_fn(self.test_input)
        assert key1 == key2
    
    def test_idempotency_different_input_different_key(self):
        """不同输入产生不同幂等键"""
        key1 = self.tool.idempotency_key_fn(self.test_input_1)
        key2 = self.tool.idempotency_key_fn(self.test_input_2)
        assert key1 != key2
    
    def test_double_execution_same_result(self):
        """连续执行两次，结果相同"""
        result1 = self.tool.execute(self.test_input)
        result2 = self.tool.execute(self.test_input)
        assert result1 == result2


class CompensatableToolTestMixin:
    """可补偿工具测试混入"""
    
    def test_compensation_reverses_effect(self):
        """补偿能撤销副作用"""
        # 执行
        result = self.tool.execute(self.test_input)
        
        # 验证副作用存在
        assert self.verify_side_effect_exists()
        
        # 补偿
        compensated = self.tool.compensate_fn(self.test_input, result)
        assert compensated
        
        # 验证副作用已撤销
        assert not self.verify_side_effect_exists()
    
    def test_compensation_is_idempotent(self):
        """补偿本身是幂等的"""
        result = self.tool.execute(self.test_input)
        
        # 补偿两次
        self.tool.compensate_fn(self.test_input, result)
        self.tool.compensate_fn(self.test_input, result)
        
        # 不应报错，状态一致
```

---

## 补充章节 5：Skills 供应链治理落地

### 5.1 签名链

```
┌─────────────────────────────────────────────────────────────┐
│                      签名链架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  组织 Root CA                                               │
│       │                                                     │
│       ├── Skills Signing CA（技能签名CA）                   │
│       │       │                                             │
│       │       ├── CI/CD 签名证书                            │
│       │       │   └── 自动构建的技能                        │
│       │       │                                             │
│       │       └── 人工审批签名证书                          │
│       │           └── 敏感技能（需要人工审批）               │
│       │                                                     │
│       └── Developer CA（开发者CA）                          │
│               └── 开发环境技能（仅限测试）                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

```python
class SkillSignatureVerifier:
    """技能签名验证器"""
    
    def __init__(self, trust_store: TrustStore):
        self.trust_store = trust_store
    
    def verify(self, skill_path: str, signature: SkillSignature) -> VerifyResult:
        """
        验证技能签名
        1. 验证签名证书链
        2. 验证签名有效性
        3. 检查证书是否在吊销列表
        4. 检查签名时间戳
        """
        # 1. 加载证书链
        cert_chain = signature.certificate_chain
        
        # 2. 验证证书链到可信根
        if not self._verify_chain(cert_chain, self.trust_store.root_ca):
            return VerifyResult(valid=False, reason="Certificate chain verification failed")
        
        # 3. 检查吊销
        if self._is_revoked(cert_chain[0]):
            return VerifyResult(valid=False, reason="Signing certificate revoked")
        
        # 4. 验证签名
        skill_hash = self._hash_skill_content(skill_path)
        if not self._verify_signature(skill_hash, signature.signature_value, cert_chain[0]):
            return VerifyResult(valid=False, reason="Signature verification failed")
        
        # 5. 检查时间戳（防止重放）
        if signature.timestamp < self._get_min_valid_timestamp():
            return VerifyResult(valid=False, reason="Signature too old")
        
        return VerifyResult(
            valid=True,
            signer=cert_chain[0].subject,
            signed_at=signature.timestamp,
            trust_level=self._get_trust_level(cert_chain)
        )
```

### 5.2 Hash Pin 与 SBOM

```yaml
# skill_manifest.yaml - 技能清单文件
name: financial_compliance
version: 2.1.0
signature: "sha256:abc123..."

# 内容哈希锁定
content_hashes:
  SKILL.md: "sha256:def456..."
  compliance_rules.md: "sha256:ghi789..."
  scripts/validate_transaction.py: "sha256:jkl012..."

# 依赖声明（SBOM - Software Bill of Materials）
dependencies:
  - name: "base_financial_skill"
    version: "1.0.0"
    hash: "sha256:mno345..."
    source: "internal://skills/base_financial"
  
  - name: "python-dateutil"
    version: "2.8.2"
    hash: "sha256:pqr678..."
    source: "pypi://python-dateutil"
    vulnerability_scan:
      scanned_at: "2024-12-01T00:00:00Z"
      cve_count: 0

# 安全扫描结果
security_scan:
  scanner_version: "1.2.0"
  scanned_at: "2024-12-15T10:30:00Z"
  findings:
    - severity: "low"
      rule: "hardcoded_path"
      location: "scripts/validate_transaction.py:42"
      status: "accepted"  # 已评审接受
      accepted_by: "security@company.com"
      accepted_at: "2024-12-15T11:00:00Z"
```

### 5.3 Sandbox 配置

```python
class SkillSandbox:
    """技能执行沙箱"""
    
    # 默认沙箱配置
    DEFAULT_CONFIG = SandboxConfig(
        # 文件系统
        filesystem=FilesystemPolicy(
            read_paths=["/skills/current", "/tmp/skill_workspace"],
            write_paths=["/tmp/skill_workspace"],
            forbidden_paths=["/etc", "/var", "/home", "/root"],
        ),
        
        # 网络
        network=NetworkPolicy(
            allowed_hosts=["internal-api.company.com"],
            forbidden_hosts=["*"],  # 默认禁止所有外部
            max_connections=10,
        ),
        
        # 资源限制
        resources=ResourceLimits(
            max_memory_mb=512,
            max_cpu_seconds=30,
            max_file_size_mb=10,
            max_files_open=100,
        ),
        
        # 系统调用
        syscalls=SyscallPolicy(
            allowed=["read", "write", "open", "close", "stat", ...],
            forbidden=["exec", "fork", "clone", "ptrace", ...],
        ),
    )
    
    async def execute_script(
        self, 
        script_path: str, 
        args: dict,
        config: Optional[SandboxConfig] = None
    ) -> ScriptResult:
        """在沙箱中执行脚本"""
        config = config or self.DEFAULT_CONFIG
        
        # 创建隔离环境
        container = await self._create_container(config)
        
        try:
            # 复制脚本到沙箱
            await container.copy_in(script_path, "/sandbox/script.py")
            
            # 执行
            result = await container.exec(
                cmd=["python", "/sandbox/script.py"],
                env=self._sanitize_env(args),
                timeout=config.resources.max_cpu_seconds
            )
            
            return ScriptResult(
                success=result.exit_code == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                resource_usage=result.resource_usage
            )
        finally:
            await container.destroy()
```

### 5.4 审批流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      技能发布审批流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 开发者提交                                                      │
│     └── 创建 PR，包含 skill_manifest.yaml                          │
│                                                                     │
│  2. 自动检查（CI）                                                  │
│     ├── Schema 验证                                                 │
│     ├── Hash 计算并写入 manifest                                   │
│     ├── 依赖扫描（CVE检查）                                        │
│     ├── 静态安全扫描                                                │
│     │   ├── Prompt injection patterns                              │
│     │   ├── 敏感信息硬编码                                         │
│     │   ├── 危险系统调用                                           │
│     │   └── 权限提升尝试                                           │
│     └── 沙箱测试（在隔离环境运行）                                  │
│                                                                     │
│  3. 人工审批（根据风险级别）                                        │
│     ├── LOW: 自动通过（仅 read-only 技能）                         │
│     ├── MEDIUM: 1人审批（普通技能）                                │
│     ├── HIGH: 2人审批（涉及敏感数据/外部调用）                      │
│     └── CRITICAL: 安全团队审批（涉及核心系统）                      │
│                                                                     │
│  4. 签名与发布                                                      │
│     ├── CI 签名（普通技能）或 人工签名（敏感技能）                  │
│     ├── 写入技能仓库                                                │
│     └── 更新 SBOM                                                   │
│                                                                     │
│  5. 灰度发布                                                        │
│     ├── 1% 流量（观察24小时）                                      │
│     ├── 10% 流量（观察24小时）                                     │
│     ├── 50% 流量（观察24小时）                                     │
│     └── 100% 流量                                                   │
│                                                                     │
│  6. 回滚能力                                                        │
│     └── 任何阶段发现问题，1分钟内回滚到上一稳定版本                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 补充章节 6：验证器与 Harness 资产化

### 6.1 验证器资产管理

```python
class ValidatorRegistry:
    """验证器注册表 - 把验证器当作资产管理"""
    
    def __init__(self):
        self.validators = {}
        self.golden_cases = {}
        self.performance_baselines = {}
    
    def register(
        self, 
        validator: Validator,
        golden_cases: List[GoldenCase],
        baseline: PerformanceBaseline
    ):
        """
        注册验证器
        必须同时提供：
        - 验证器实现
        - Golden cases（黄金测试用例）
        - 性能基线
        """
        # 验证 golden cases 覆盖率
        coverage = self._check_coverage(validator, golden_cases)
        if coverage < 0.8:
            raise InsufficientCoverage(f"Golden case coverage {coverage} < 0.8")
        
        # 运行 golden cases 验证验证器本身
        for case in golden_cases:
            result = validator.validate(case.task, case.result)
            if result.status != case.expected_status:
                raise GoldenCaseFailed(case)
        
        self.validators[validator.name] = validator
        self.golden_cases[validator.name] = golden_cases
        self.performance_baselines[validator.name] = baseline


@dataclass
class GoldenCase:
    """黄金测试用例"""
    case_id: str
    description: str
    task: Task
    result: Result
    expected_status: DoneStatus
    expected_evidence: List[str]
    tags: List[str]  # e.g., ["edge_case", "regression", "security"]
    added_at: datetime
    added_by: str
    last_verified: datetime
```

### 6.2 Flaky 管理

```python
class FlakyManager:
    """Flaky 验证器管理"""
    
    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold  # 5% flaky rate 触发告警
        self.history = {}
    
    def record(self, validator_name: str, result: ValidationResult):
        """记录验证结果"""
        if validator_name not in self.history:
            self.history[validator_name] = deque(maxlen=1000)
        
        self.history[validator_name].append({
            "timestamp": now(),
            "status": result.status,
            "latency_ms": result.latency_ms,
            "inconclusive": result.status == DoneStatus.INCONCLUSIVE
        })
    
    def get_flaky_rate(self, validator_name: str, window_hours: int = 24) -> float:
        """计算 flaky rate（INCONCLUSIVE 比例）"""
        history = self.history.get(validator_name, [])
        recent = [h for h in history if h["timestamp"] > now() - hours(window_hours)]
        
        if not recent:
            return 0.0
        
        inconclusive_count = sum(1 for h in recent if h["inconclusive"])
        return inconclusive_count / len(recent)
    
    def should_skip(self, validator_name: str) -> bool:
        """
        是否应该跳过该验证器
        flaky rate 过高时自动跳过，避免阻塞流程
        """
        rate = self.get_flaky_rate(validator_name)
        if rate > self.threshold:
            # 记录告警
            alert(f"Validator {validator_name} flaky rate {rate:.2%} > {self.threshold:.2%}")
            return True
        return False
    
    def get_health_report(self) -> HealthReport:
        """健康报告"""
        return HealthReport(
            validators=[
                ValidatorHealth(
                    name=name,
                    flaky_rate=self.get_flaky_rate(name),
                    avg_latency_ms=self._avg_latency(name),
                    p99_latency_ms=self._p99_latency(name),
                    status="healthy" if self.get_flaky_rate(name) < self.threshold else "degraded"
                )
                for name in self.history
            ]
        )
```

### 6.3 验收 SLA

```yaml
# validator_sla.yaml - 验证器服务等级协议

validators:
  build_validator:
    description: "代码构建验证"
    sla:
      availability: 99.9%           # 可用性
      max_latency_p99_ms: 60000    # P99延迟上限（60秒）
      max_flaky_rate: 2%           # 最大flaky率
      max_false_positive_rate: 1%  # 最大误报率
      max_false_negative_rate: 0.1% # 最大漏报率（更严格）
    
    escalation:
      degraded:                     # 降级处理
        condition: "flaky_rate > 5% OR latency_p99 > 120s"
        action: "switch_to_fallback_validator"
      
      critical:                     # 严重故障
        condition: "availability < 95% OR false_negative_rate > 1%"
        action: "page_oncall AND pause_deployments"
    
    golden_case_requirements:
      min_count: 50
      must_include_tags: ["happy_path", "edge_case", "error_handling"]
      refresh_frequency: "weekly"

  reconciliation_validator:
    description: "金融对账验证"
    sla:
      availability: 99.99%          # 更高可用性要求
      max_latency_p99_ms: 300000   # 5分钟（对账可能较慢）
      max_flaky_rate: 1%
      max_false_positive_rate: 0.5%
      max_false_negative_rate: 0%   # 金融场景不允许漏报
    
    escalation:
      degraded:
        condition: "flaky_rate > 2%"
        action: "switch_to_manual_verification"
      
      critical:
        condition: "any false_negative detected"
        action: "halt_all_transactions AND page_cfo"
```

### 6.4 基准测试框架

```python
class HarnessBenchmark:
    """Harness 基准测试框架"""
    
    def __init__(self, validator_registry: ValidatorRegistry):
        self.registry = validator_registry
    
    async def run_benchmark(self, validator_name: str) -> BenchmarkResult:
        """运行基准测试"""
        validator = self.registry.validators[validator_name]
        golden_cases = self.registry.golden_cases[validator_name]
        baseline = self.registry.performance_baselines[validator_name]
        
        results = []
        
        for case in golden_cases:
            start = time.time()
            result = await validator.validate(case.task, case.result)
            latency_ms = (time.time() - start) * 1000
            
            results.append({
                "case_id": case.case_id,
                "expected": case.expected_status,
                "actual": result.status,
                "correct": result.status == case.expected_status,
                "latency_ms": latency_ms
            })
        
        # 计算指标
        accuracy = sum(1 for r in results if r["correct"]) / len(results)
        avg_latency = sum(r["latency_ms"] for r in results) / len(results)
        p99_latency = percentile([r["latency_ms"] for r in results], 99)
        
        # 与基线比较
        regression = BenchmarkRegression(
            accuracy_delta=accuracy - baseline.accuracy,
            latency_delta_pct=(avg_latency - baseline.avg_latency_ms) / baseline.avg_latency_ms,
            is_regression=accuracy < baseline.accuracy * 0.99 or avg_latency > baseline.avg_latency_ms * 1.2
        )
        
        return BenchmarkResult(
            validator_name=validator_name,
            timestamp=now(),
            total_cases=len(results),
            accuracy=accuracy,
            avg_latency_ms=avg_latency,
            p99_latency_ms=p99_latency,
            baseline=baseline,
            regression=regression,
            details=results
        )
    
    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """运行所有验证器的基准测试"""
        results = []
        for name in self.registry.validators:
            result = await self.run_benchmark(name)
            results.append(result)
            
            if result.regression.is_regression:
                alert(f"Benchmark regression detected for {name}: {result.regression}")
        
        return results
```

---

## 附录：Model Router 修正

### 原方案问题
> "complexity 估计是玄学"

### 修正方案：验证驱动升级

```python
class AdaptiveModelRouter:
    """
    自适应模型路由
    原则：先用便宜模型，验证失败再升级
    """
    
    def __init__(self, ...):
        self.model_tiers = [
            "gpt-4o-mini",      # Tier 0: 最便宜
            "claude-haiku",     # Tier 1
            "gpt-4o",           # Tier 2
            "claude-sonnet",    # Tier 3
            "claude-opus",      # Tier 4: 最贵
        ]
    
    async def call_with_upgrade(
        self,
        task: Task,
        context: ExecutionContext,
        validator: Optional[Validator] = None
    ) -> LLMResponse:
        """
        验证驱动的模型升级
        1. 从最便宜的模型开始
        2. 如果验证失败/INCONCLUSIVE，升级到下一档
        3. 直到成功或用完所有模型
        """
        start_tier = self._get_start_tier(task, context)
        
        for tier in range(start_tier, len(self.model_tiers)):
            model = self.model_tiers[tier]
            
            # 预算检查
            if not self.budget_manager.can_afford(model):
                continue
            
            # 调用
            response = await self.call(model, task.prompt)
            
            # 如果没有验证器，直接返回
            if not validator:
                return response
            
            # 验证
            validation = await validator.validate(task, response)
            
            if validation.status == DoneStatus.DONE:
                # 成功，记录这个任务类型适合什么模型
                self._record_success(task.type, tier)
                return response
            
            if validation.status == DoneStatus.NOT_DONE:
                # 失败，升级模型
                self._record_failure(task.type, tier, validation.reason)
                continue
            
            if validation.status == DoneStatus.INCONCLUSIVE:
                # 不确定，根据策略决定
                if self._should_retry_with_same_model(task, tier):
                    continue
                else:
                    # 升级
                    continue
        
        # 所有模型都试过了
        raise AllModelsExhausted(task)
    
    def _get_start_tier(self, task: Task, context: ExecutionContext) -> int:
        """
        根据历史数据决定起始档位
        不是猜测 complexity，而是基于同类任务的历史成功率
        """
        history = self.success_history.get(task.type, {})
        
        # 找到历史成功率 > 80% 的最便宜模型
        for tier in range(len(self.model_tiers)):
            if history.get(tier, {}).get("success_rate", 0) > 0.8:
                return tier
        
        # 无历史数据，从最便宜开始
        return 0
```

---

## 文档版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | - | 初始架构，P0三件套 + PolicyEngine |
| v2.1 | - | 补充6个落地细则章节 |

**v2.1 补充内容：**
1. ✅ 并行/多 Agent 模型（Task Lease、Single Writer、冲突策略）
2. ✅ Event Schema 演进（版本控制、迁移器、SoT边界修正）
3. ✅ Data Egress Gateway（出站总闸、策略矩阵）
4. ✅ Tool 合同落地清单（各级别checklist、测试模板）
5. ✅ Skills 供应链治理（签名链、SBOM、Sandbox、审批流）
6. ✅ 验证器资产化（Golden Cases、Flaky管理、SLA、基准测试）
7. ✅ Model Router 修正（验证驱动升级替代complexity估计）

---

*文档状态：可进入银行级架构评审*
