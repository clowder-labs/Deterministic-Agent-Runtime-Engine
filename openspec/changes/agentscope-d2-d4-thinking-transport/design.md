## Context

当前主干中，模型响应类型仅保留 `content/tool_calls/usage`，无法承载推理内容；transport 事件类型仍以 `result/error/hook` 为主，难以表达 AgentScope 语义中的中间态事件。已有示例（example 10）通过 compat shim 模拟了该能力，但框架本体未提供同等契约。

## Goals / Non-Goals

**Goals:**
- 在框架本体补齐 D2 + D4 需要的最小可用契约。
- 统一 transport 中间态事件分类与错误 payload。
- 在 adapter 层保留并规范化 `thinking_content` 与 `reasoning_tokens`。
- 在 ReAct 执行循环中发射可观测中间态事件，支持端到端消费。

**Non-Goals:**
- 不在本切片实现 streaming 生成接口（`generate_stream`）。
- 不在本切片改造 session 持久化协议（S1/S2）。
- 不引入新 provider adapter。

## Decisions

1. **事件语义分层**
- Decision: 保留 `TransportEnvelope.event_type` 为字符串字段，但增加一组 canonical 枚举值覆盖 `message/tool_call/tool_result/thinking/error/status`，并维护 legacy alias 到 canonical 的归一化映射。
- Rationale: 最小化对现有 transport 调度器的侵入，同时让调用侧获得稳定语义。
- Alternative considered: 直接替换现有 `RESULT/HOOK` 枚举并删除兼容映射；该方案会扩大回归面，暂不采用。

2. **模型响应扩展策略**
- Decision: 在 `ModelResponse` 新增可选 `thinking_content` 字段；`usage` 继续使用 dict，但要求 adapter 将 `reasoning_tokens` 规范化写入。
- Rationale: 维持现有调用接口，避免一次性引入新的 usage 强类型模型。
- Alternative considered: 引入全新 `Usage` dataclass；当前改动成本与兼容风险较高。

3. **中间态事件发射位置**
- Decision: 在 ReAct 主循环中，在模型返回后、工具调用前后发射 thinking/tool_call/tool_result 事件。
- Rationale: 该位置可精确覆盖执行时序，且无需新增 channel 层。
- Alternative considered: 在 tool gateway 或 transport channel 内部推导事件；会丢失模型 thinking 阶段信息。

4. **测试策略**
- Decision: 采用“单元契约 + 端到端序列”双层验证：
  - transport 类型与 payload/error 契约单测；
  - adapter thinking/usage 提取单测；
  - agent 到 transport 的事件序列回归测试。
- Rationale: 保证接口稳定且行为可观测。

## Risks / Trade-offs

- [Risk] 旧消费者依赖 `result/hook` 事件语义。 → Mitigation: 保留 alias 归一化并增加回归测试。
- [Risk] 不同 provider 的 thinking 字段路径不一致。 → Mitigation: 在 adapter 层集中解析并提供降级为 `None` 的一致行为。
- [Risk] 事件发射增多带来日志噪声。 → Mitigation: 仅输出必要字段，后续在 D8 切片补采样/脱敏。

## Migration Plan

1. 先扩展类型定义（transport/model），保证兼容映射存在。
2. 再落地 adapter 提取逻辑（thinking + reasoning_tokens）。
3. 接入 ReAct loop 事件发射，并补充序列测试。
4. 运行定向测试与全量回归；更新 TODO/feature evidence。

Rollback:
- 若出现兼容问题，可回退到旧事件映射并关闭中间态事件发射路径；类型扩展为向后兼容，不影响核心调用。

## Open Questions

- `status` 事件在当前 D2 切片中是否仅作为保留类型，还是立即要求具体 payload 结构？
- `thinking_content` 是否需要在后续切片中加入脱敏策略（例如 prompt 注入片段清理）？
