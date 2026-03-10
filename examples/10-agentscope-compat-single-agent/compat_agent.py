"""Example 10: AgentScope-equivalent single-agent compatibility layer.

This module provides a runnable single-agent demo built on top of dare_framework
while exposing AgentScope-like concepts. It serves as:

1. A migration reference showing how each AgentScope capability maps to DARE
2. A gap analysis tool — stubs/placeholders mark capabilities not yet in framework
3. A runnable validation that the core ReAct loop works end-to-end

AgentScope capabilities covered (12 total):
  ReActAgent / Msg / TextBlock / Tool / InMemoryMemory / ChatModelBase /
  PlanNoteBook / SubTask / TruncatedFormatterBase / Knowledge /
  HttpStatefulClient / Session

Gap Reference: docs/design/agentscope-migration-framework-gaps.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import Context, Message
from dare_framework.knowledge import create_knowledge
from dare_framework.mcp.client import MCPClient
from dare_framework.mcp.transports.http import HTTPTransport
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse
from dare_framework.tool.kernel import ITool, IToolProvider
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)
from dare_framework.transport.kernel import AgentChannel


# ===========================================================================
# Gap Stubs: 框架层缺失的能力声明（待框架补齐后替换为真实实现）
# 这些 stub 标注了 Gap ID，与 docs/design/agentscope-migration-framework-gaps.md 对应
# ===========================================================================


class MessageTag:
    """[STUB - Gap-M1] 消息标签枚举。

    AgentScope 的 InMemoryMemory 支持对消息打 mark，
    用于压缩策略感知和消息过滤。

    框架补齐后应为 str Enum，定义在 dare_framework/context/types.py。
    """

    REASONING = "reasoning"      # 模型推理过程（thinking block）
    COMPRESSED = "compressed"    # 被摘要折叠过的消息
    IMPORTANT = "important"      # 重要消息，压缩时不得丢弃
    TOOL_CALL = "tool_call"      # 工具调用消息
    TOOL_RESULT = "tool_result"  # 工具结果消息


class StateModule:
    """[STUB - Gap-S1] 通用状态模块协议。

    AgentScope 的 Session 系统依赖 StateModule 协议：
    每个组件（memory, toolkit, plan_notebook）实现 state_dict()/load_state_dict()，
    Session 统一调用实现模块化持久化。

    框架补齐后应为 Protocol，定义在 dare_framework/session/kernel.py。
    """

    def state_dict(self) -> dict[str, Any]:
        """序列化组件状态为 dict。"""
        raise NotImplementedError("StateModule.state_dict() - Gap-S1: 待框架实现")

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """从 dict 恢复组件状态。"""
        raise NotImplementedError("StateModule.load_state_dict() - Gap-S1: 待框架实现")


class ISessionStore:
    """[STUB - Gap-S2] Session 持久化接口。

    AgentScope: SessionBase.save_session_state(session_id, user_id, **state_modules)
    DARE: 无等价接口。

    框架补齐后应为 Protocol，定义在 dare_framework/session/kernel.py。
    """

    async def save(self, session_id: str, user_id: str = "",
                   **modules: StateModule) -> None:
        raise NotImplementedError("ISessionStore.save() - Gap-S2: 待框架实现")

    async def load(self, session_id: str, user_id: str = "",
                   allow_not_exist: bool = True,
                   **modules: StateModule) -> None:
        raise NotImplementedError("ISessionStore.load() - Gap-S2: 待框架实现")


# ===========================================================================
# Capability 1: Msg — 消息结构桥接
# AgentScope: Msg(id, name, role, content: str|list[ContentBlock], metadata, timestamp)
# DARE:       Message(role, kind, text, attachments, data, name, metadata)
# Gap-M1: 无 tag 字段  Gap-M2: 无原生 ContentBlock 体系  Gap-M3: 无 id  Gap-M5: 无序列化
# ===========================================================================


class TextBlock(TypedDict):
    """Capability 3: TextBlock — AgentScope ContentBlock 体系之一。

    AgentScope 支持 TextBlock/ThinkingBlock/ImageBlock/AudioBlock/VideoBlock/
    ToolUseBlock/ToolResultBlock 联合类型。
    DARE Message.text 为主，无原生 ContentBlock 体系 [Gap-M2]。
    """

    type: Literal["text"]
    text: str


class ThinkingBlock(TypedDict):
    """[STUB - Gap-LM1] ThinkingBlock — 模型推理内容块。

    AgentScope: ThinkingBlock(type="thinking", thinking=str)
    DARE: ModelResponse 无 thinking_content 字段，推理内容丢失。

    框架补齐 Gap-LM1 后，ModelResponse.thinking_content 将携带此内容，
    并通过 MessageTag.REASONING 标记存入 STM。
    """

    type: Literal["thinking"]
    thinking: str


# ContentBlock 联合类型（AgentScope 完整体系的子集）
ContentBlock = TextBlock | ThinkingBlock


@dataclass
class CompatMsg:
    """Capability 2: Msg 兼容桥接。

    AgentScope Msg 与 DARE Message 的双向转换。

    当前限制（受框架 Gap 影响）：
    - [Gap-M1] 转换时 tag 信息丢失（Message 无 tag 字段）
    - [Gap-M2] 多模态内容块（ImageBlock 等）强制转为纯文本
    - [Gap-M3] id 字段由 CompatMsg 自管理，不持久化到 Message
    - [Gap-LM1] ThinkingBlock 转换为纯文本拼接，无法区分推理/正文
    """

    id: str
    name: str
    role: str
    blocks: list[ContentBlock]
    metadata: dict[str, Any] = field(default_factory=dict)
    tag: str | None = None  # [Gap-M1] 模拟 MessageTag，框架补齐后迁移到 Message.tag

    @classmethod
    def from_framework_message(cls, message: Message) -> "CompatMsg":
        # [Gap-M3] Message 无 id 字段，此处生成临时 id
        msg_id = message.metadata.get("_compat_id", str(uuid.uuid4())[:8])
        # [Gap-M1] Message 无 tag 字段，从 metadata 读取过渡标记
        tag = message.metadata.get("_compat_tag")
        blocks: list[ContentBlock] = []
        if message.kind == "thinking" and message.text:
            blocks.append({"type": "thinking", "thinking": message.text})
        elif message.text is not None:
            blocks.append({"type": "text", "text": message.text})
        # 兼容桥仅实现 TextBlock/ThinkingBlock；附件在此处退化为文本占位。
        for attachment in message.attachments:
            blocks.append({"type": "text", "text": f"[{attachment.kind}] {attachment.uri}"})
        compat_metadata = {
            k: v for k, v in message.metadata.items()
            if not k.startswith("_compat_")
        }
        if isinstance(message.data, dict):
            tool_calls = message.data.get("tool_calls")
            if isinstance(tool_calls, list) and "tool_calls" not in compat_metadata:
                compat_metadata["tool_calls"] = tool_calls
        return cls(
            id=msg_id,
            name=message.name or str(message.role),
            role=str(message.role),
            blocks=blocks or [{"type": "text", "text": ""}],
            metadata=compat_metadata,
            tag=tag,
        )

    def to_framework_message(self) -> Message:
        text_parts = []
        message_kind = "chat"
        for block in self.blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "thinking":
                message_kind = "thinking"
                text_parts.append(block.get("thinking", ""))
        metadata = dict(self.metadata)
        metadata["_compat_id"] = self.id
        if self.tag:
            metadata["_compat_tag"] = self.tag
        data: dict[str, Any] | None = None
        tool_calls = metadata.get("tool_calls")
        if isinstance(tool_calls, list):
            data = {"tool_calls": tool_calls}
        return Message(
            role=self.role,
            kind=message_kind,
            text="\n".join(text_parts),
            data=data,
            name=self.name,
            metadata=metadata,
        )


# ===========================================================================
# Capability 9: TruncatedFormatterBase — 截断格式化器
# AgentScope: token 级截断 + tool pair 安全 + provider-specific 格式化
# DARE:       compress_context() 按消息条数截断，无 tool pair 安全 [Gap-F1]
# ===========================================================================


@dataclass(frozen=True)
class FormattedPrompt:
    """Formatter output with truncation statistics."""

    messages: list[dict[str, Any]]
    total_chars: int
    removed_count: int


class CompatTruncatedFormatter:
    """Capability 9: TruncatedFormatterBase 兼容实现。

    实现了 AgentScope TruncatedFormatterBase 的核心行为：
    - 字符预算截断（AgentScope 用 token，此处用字符数作简化）[Gap-F2]
    - tool call/result 配对保护 — 成对删除不孤儿化 [补齐 Gap-F1]
    - 保留 system 消息不截断

    当前限制（受框架 Gap 影响）：
    - [Gap-F2] 基于字符数而非 token 数，因框架无 token 计数接口
    - [Gap-F3] 无 provider-specific 格式化（OpenAI/Anthropic/Gemini 消息格式不同）
    - [Gap-F4] 需手动调用，框架层无自动触发机制
    - [Gap-M1] 无法感知 MessageTag.IMPORTANT，所有非 system 消息平等对待
    """

    def __init__(self, max_chars: int) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        self._max_chars = max_chars

    def format(self, messages: list[Message]) -> FormattedPrompt:
        normalized = [CompatMsg.from_framework_message(message) for message in messages]
        serialized = [self._serialize_message(msg) for msg in normalized]
        total_chars = self._count_chars(serialized)
        removed_count = 0

        while total_chars > self._max_chars and len(serialized) > 1:
            remove_index = 1 if serialized[0].get("role") == "system" else 0
            if remove_index >= len(serialized):
                break

            removed = self._drop_with_tool_pair(serialized, remove_index)
            removed_count += removed
            total_chars = self._count_chars(serialized)

        return FormattedPrompt(
            messages=serialized,
            total_chars=total_chars,
            removed_count=removed_count,
        )

    def _serialize_message(self, message: CompatMsg) -> dict[str, Any]:
        return {
            "name": message.name,
            "role": message.role,
            "content": list(message.blocks),
            "metadata": dict(message.metadata),
        }

    def _drop_with_tool_pair(
        self,
        messages: list[dict[str, Any]],
        start_index: int,
    ) -> int:
        """删除消息时保护 tool call/result 配对完整性。

        这是 Gap-F1 的 Example 层补齐：框架的 compress_context() 不具备此能力。
        当框架补齐 Gap-F1 (compress_context(tool_pair_safe=True)) 后，
        此方法应迁移到框架层。
        """
        removed_count = 0
        removed_tool_ids: set[str] = set()
        target = messages[start_index]
        target_role = str(target.get("role", ""))

        if target_role == "assistant":
            for call in target.get("metadata", {}).get("tool_calls", []):
                tool_id = str(call.get("id", "")).strip()
                if tool_id:
                    removed_tool_ids.add(tool_id)
            del messages[start_index]
            removed_count += 1
            cursor = start_index
            while cursor < len(messages):
                msg = messages[cursor]
                if str(msg.get("role", "")) != "tool":
                    cursor += 1
                    continue
                tool_name = str(msg.get("name", "")).strip()
                if tool_name in removed_tool_ids:
                    del messages[cursor]
                    removed_count += 1
                    continue
                cursor += 1
            return removed_count

        if target_role == "tool":
            tool_name = str(target.get("name", "")).strip()
            if start_index > 0:
                previous = messages[start_index - 1]
                if str(previous.get("role", "")) == "assistant":
                    previous_ids = {
                        str(call.get("id", "")).strip()
                        for call in previous.get("metadata", {}).get("tool_calls", [])
                    }
                    if tool_name and tool_name in previous_ids:
                        del messages[start_index]
                        del messages[start_index - 1]
                        return 2
            del messages[start_index]
            return 1

        del messages[start_index]
        return 1

    def _count_chars(self, messages: list[dict[str, Any]]) -> int:
        total = 0
        for item in messages:
            for block in item.get("content", []):
                total += len(str(block.get("text", block.get("thinking", ""))))
            metadata = item.get("metadata", {})
            if metadata:
                total += len(json.dumps(metadata, ensure_ascii=False))
        return total


# ===========================================================================
# Capability 6: ChatModelBase — 模型适配器包装
# AgentScope: ChatModelBase.__call__(messages, stream=True/False)
# DARE:       IModelAdapter.generate(model_input, options)
# Gap-LM1: 无 thinking_content  Gap-LM2: 无 streaming
# ===========================================================================


class CompatFormattedModelAdapter(IModelAdapter):
    """Capability 6 + 9: 格式化 + 模型适配。

    包装任意 IModelAdapter，在模型调用前应用 CompatTruncatedFormatter。

    当前限制（受框架 Gap 影响）：
    - [Gap-LM1] thinking_content 丢失：inner adapter 不提取 reasoning_content
    - [Gap-LM2] 无流式输出：generate() 阻塞等待完整响应
    - [Gap-LM4] usage 中 reasoning_tokens 未规范化
    """

    def __init__(self, inner: IModelAdapter, formatter: CompatTruncatedFormatter) -> None:
        self._inner = inner
        self._formatter = formatter

    @property
    def name(self) -> str:
        return f"{self._inner.name}-compat-formatted"

    @property
    def model(self) -> str:
        return self._inner.model

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        formatted = self._formatter.format(model_input.messages)
        delegated_input = ModelInput(
            messages=[self._formatted_to_message(item) for item in formatted.messages],
            tools=list(model_input.tools),
            metadata={
                **dict(model_input.metadata),
                "compat_formatter": {
                    "total_chars": formatted.total_chars,
                    "removed_count": formatted.removed_count,
                },
            },
        )
        response = await self._inner.generate(delegated_input, options=options)
        # [Gap-LM1] thinking_content 在此处应被提取并存入 ModelResponse.thinking_content
        # 目前 ModelResponse 无此字段，推理内容直接丢失
        return ModelResponse(
            content=response.content,
            tool_calls=list(response.tool_calls),
            usage=response.usage,
            metadata={
                **dict(response.metadata),
                "compat_formatter": {
                    "total_chars": formatted.total_chars,
                    "removed_count": formatted.removed_count,
                },
            },
        )

    async def generate_stream(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """[STUB - Gap-LM2] 流式生成。

        AgentScope: ChatModelBase.__call__(stream=True) 返回 AsyncGenerator
        DARE: IModelAdapter 无 generate_stream() 方法

        框架补齐后应返回 AsyncIterator[ModelResponseChunk]。
        当前 fallback 到非流式 generate()。
        """
        return await self.generate(model_input, options=options)

    def _formatted_to_message(self, item: dict[str, Any]) -> Message:
        blocks = item.get("content", [])
        text = "\n".join(str(block.get("text", "")) for block in blocks if isinstance(block, dict))
        metadata = dict(item.get("metadata", {}))
        data: dict[str, Any] | None = None
        kind = "chat"
        tool_calls = metadata.get("tool_calls")
        if isinstance(tool_calls, list):
            data = {"tool_calls": tool_calls}
            kind = "tool_call"
        elif any(isinstance(block, dict) and block.get("type") == "thinking" for block in blocks):
            kind = "thinking"
        if str(item.get("role", "user")) == "tool":
            tool_call_id = item.get("name")
            if isinstance(tool_call_id, str) and tool_call_id.strip():
                data = {**(data or {}), "tool_call_id": tool_call_id}
            kind = "tool_result"
        return Message(
            role=str(item.get("role", "user")),
            kind=kind,
            text=text,
            data=data,
            name=item.get("name"),
            metadata=metadata,
        )


# ===========================================================================
# Capability 5: InMemoryMemory — 带标记的工作记忆
# AgentScope: list[(Msg, marks)] + mark/filter/compressed_summary/state_dict
# DARE:       InMemorySTM — list[Message], 无标记、无序列化
# ===========================================================================


class CompatMemoryWrapper:
    """[STUB - Gap-Mem1/Mem2/Mem3] InMemoryMemory 等价能力包装。

    在 DARE 的 Context/STM 之上模拟 AgentScope InMemoryMemory 的扩展能力。

    当前限制：
    - [Gap-Mem1] mark/tag 系统通过 metadata 模拟，框架层无原生支持
    - [Gap-Mem2] compressed_summary 自管理，框架 STM 无此概念
    - [Gap-Mem3] state_dict() 需手动遍历 STM，框架 InMemorySTM 无此方法
    - [Gap-Mem4] 无按 ID 删除，Message 无 id 字段
    - [Gap-Mem5] compress 不保护 tool pair，需用 CompatTruncatedFormatter 替代
    """

    def __init__(self, context: Context) -> None:
        self._context = context
        self._compressed_summary: str = ""
        self._marks: dict[str, list[str]] = {}  # msg_id -> [mark1, mark2, ...]

    def add(self, message: Message, marks: list[str] | None = None) -> None:
        """添加消息并可选打标。"""
        msg_id = message.metadata.get("_compat_id", str(uuid.uuid4())[:8])
        if "_compat_id" not in message.metadata:
            message = Message(
                role=message.role,
                kind=message.kind,
                text=message.text,
                attachments=list(message.attachments),
                data=dict(message.data) if isinstance(message.data, dict) else None,
                name=message.name,
                metadata={**message.metadata, "_compat_id": msg_id},
            )
        self._context.stm_add(message)
        if marks:
            self._marks[msg_id] = list(marks)

    def get_memory(
        self,
        mark: str | None = None,
        exclude_mark: str | None = None,
        prepend_summary: bool = False,
    ) -> list[Message]:
        """[Gap-Mem1] 按标签过滤检索，模拟 AgentScope get_memory()。"""
        messages = self._context.stm_get()
        if mark is not None:
            messages = [
                m for m in messages
                if mark in self._marks.get(m.metadata.get("_compat_id", ""), [])
            ]
        if exclude_mark is not None:
            messages = [
                m for m in messages
                if exclude_mark not in self._marks.get(m.metadata.get("_compat_id", ""), [])
            ]
        if prepend_summary and self._compressed_summary:
            summary_msg = Message(
                role="system",
                kind="summary",
                text=f"[Compressed Summary]\n{self._compressed_summary}",
                metadata={"_compat_tag": MessageTag.COMPRESSED},
            )
            messages = [summary_msg] + messages
        return messages

    def update_mark(self, msg_id: str, action: str, mark: str) -> None:
        """[Gap-Mem1] 更新消息标记。"""
        marks = self._marks.setdefault(msg_id, [])
        if action == "add" and mark not in marks:
            marks.append(mark)
        elif action == "remove" and mark in marks:
            marks.remove(mark)

    def update_compressed_summary(self, summary: str) -> None:
        """[Gap-Mem2] 设置压缩摘要。"""
        self._compressed_summary = summary

    def state_dict(self) -> dict[str, Any]:
        """[Gap-Mem3] 序列化 STM 状态。"""
        messages = self._context.stm_get()
        return {
            "messages": [
                {
                    "role": m.role,
                    "kind": m.kind,
                    "text": m.text,
                    "attachments": [
                        {
                            "kind": attachment.kind,
                            "uri": attachment.uri,
                            "mime_type": attachment.mime_type,
                            "filename": attachment.filename,
                            "metadata": dict(attachment.metadata),
                        }
                        for attachment in m.attachments
                    ],
                    "data": dict(m.data) if isinstance(m.data, dict) else None,
                    "name": m.name,
                    "metadata": dict(m.metadata),
                }
                for m in messages
            ],
            "marks": dict(self._marks),
            "compressed_summary": self._compressed_summary,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """[Gap-Mem3] 从 dict 恢复 STM 状态。"""
        self._context.stm_clear()
        for item in state.get("messages", []):
            self._context.stm_add(Message(
                role=item.get("role", "user"),
                kind=item.get("kind", "chat"),
                text=item.get("text"),
                attachments=item.get("attachments", []),
                data=item.get("data"),
                name=item.get("name"),
                metadata=item.get("metadata", {}),
            ))
        self._marks = state.get("marks", {})
        self._compressed_summary = state.get("compressed_summary", "")


# ===========================================================================
# Capability 7+8: PlanNoteBook + SubTask — 计划管理
# AgentScope: Plan(state, subtasks, created_at, finished_at) + 8 个工具函数
# DARE:       plan_v2.PlannerState + 6 个工具, Step 无 status [Gap-P1-P7]
# ===========================================================================


@dataclass
class CompatSubTask:
    """Capability 8: SubTask 兼容实现。

    等价于 AgentScope SubTask，包含完整生命周期状态。

    差距标注：
    - DARE plan_v2.Step 仅有 (step_id, description, params)，无生命周期 [Gap-P1]
    - DARE 无 expected_outcome/outcome 字段
    """

    name: str
    description: str
    expected_outcome: str
    state: Literal["todo", "in_progress", "done", "abandoned"] = "todo"
    outcome: str | None = None
    created_at: str = ""
    finished_at: str | None = None

    def finish(self, outcome: str) -> None:
        self.state = "done"
        self.outcome = outcome

    def to_oneline_markdown(self) -> str:
        """AgentScope SubTask.to_oneline_markdown() 等价。"""
        check = "x" if self.state == "done" else " "
        return f"- [{check}] {self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "expected_outcome": self.expected_outcome,
            "state": self.state,
            "outcome": self.outcome,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompatSubTask":
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            expected_outcome=str(data.get("expected_outcome", "")),
            state=str(data.get("state", "todo")),  # type: ignore[arg-type]
            outcome=data.get("outcome"),
            created_at=str(data.get("created_at", "")),
            finished_at=data.get("finished_at"),
        )


@dataclass
class CompatPlan:
    """Capability 7: Plan 模型。

    等价于 AgentScope Plan，包含：
    - state: 计划整体状态 [Gap-P2: DARE 无 finish_plan 工具]
    - subtasks: 有序子任务列表
    """

    name: str
    description: str
    expected_outcome: str
    subtasks: list[CompatSubTask]
    state: Literal["todo", "in_progress", "done", "abandoned"] = "todo"
    outcome: str | None = None

    def refresh_state(self) -> None:
        """根据子任务状态自动刷新计划状态。AgentScope Plan.refresh_plan_state() 等价。"""
        if not self.subtasks:
            return
        has_in_progress = any(s.state == "in_progress" for s in self.subtasks)
        has_done = any(s.state == "done" for s in self.subtasks)
        if has_in_progress or has_done:
            self.state = "in_progress"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "expected_outcome": self.expected_outcome,
            "state": self.state,
            "outcome": self.outcome,
            "subtasks": [task.to_dict() for task in self.subtasks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompatPlan":
        subtasks = [
            CompatSubTask.from_dict(item)
            for item in data.get("subtasks", [])
            if isinstance(item, dict)
        ]
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            expected_outcome=str(data.get("expected_outcome", "")),
            state=str(data.get("state", "todo")),  # type: ignore[arg-type]
            outcome=data.get("outcome"),
            subtasks=subtasks,
        )


class CompatPlanNotebook:
    """Capability 7: PlanNotebook 兼容实现。

    覆盖 AgentScope PlanNotebook 的核心 API：
    - create_plan / view_subtasks / update_subtask_state / finish_subtask / finish_plan

    差距标注：
    - [Gap-P3] 无 revise_current_plan（add/revise/delete subtask）
    - [Gap-P4] 无 view_historical_plans / recover_historical_plan
    - [Gap-P5] PlannerState 无 state_dict()，此处自行实现
    - [Gap-P6] 无 plan_change_hooks
    - [Gap-P7] 无 DefaultPlanToHint 自动注入
    """

    def __init__(self, max_subtasks: int | None = None) -> None:
        self.current_plan: CompatPlan | None = None
        self._max_subtasks = max_subtasks
        self._historical_plans: list[CompatPlan] = []
        # [Gap-P6] plan_change_hooks placeholder
        self._change_hooks: list[Any] = []

    def clear(self) -> None:
        self.current_plan = None

    def create_plan(
        self,
        *,
        name: str,
        description: str,
        expected_outcome: str,
        subtasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self._max_subtasks and len(subtasks) > self._max_subtasks:
            raise ValueError(f"too many subtasks: {len(subtasks)} > {self._max_subtasks}")
        if self.current_plan is not None:
            self._historical_plans.append(self.current_plan)
        parsed = [
            CompatSubTask(
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                expected_outcome=str(item.get("expected_outcome", "")),
            )
            for item in subtasks
        ]
        self.current_plan = CompatPlan(
            name=name,
            description=description,
            expected_outcome=expected_outcome,
            subtasks=parsed,
        )
        self._notify_change("create_plan")
        return {"created": True, "subtasks_count": len(parsed)}

    def update_subtask_state(
        self,
        subtask_idx: int,
        state: Literal["todo", "in_progress", "abandoned"],
    ) -> dict[str, Any]:
        plan = self._require_plan()
        self._check_index(plan, subtask_idx)
        plan.subtasks[subtask_idx].state = state
        plan.refresh_state()
        self._notify_change("update_subtask_state")
        return {"updated": True, "index": subtask_idx, "state": state}

    def finish_subtask(self, subtask_idx: int, subtask_outcome: str) -> dict[str, Any]:
        plan = self._require_plan()
        self._check_index(plan, subtask_idx)
        plan.subtasks[subtask_idx].finish(subtask_outcome)
        plan.refresh_state()
        self._notify_change("finish_subtask")
        return {"finished": True, "index": subtask_idx}

    def finish_plan(
        self,
        state: Literal["done", "abandoned"],
        outcome: str = "",
    ) -> dict[str, Any]:
        """[补齐 Gap-P2] 标记计划完成/放弃。AgentScope PlanNotebook.finish_plan() 等价。"""
        plan = self._require_plan()
        plan.state = state
        plan.outcome = outcome
        self._notify_change("finish_plan")
        return {"finished": True, "state": state}

    def view_subtasks(self) -> list[dict[str, Any]]:
        plan = self._require_plan()
        return [task.to_dict() for task in plan.subtasks]

    def view_historical_plans(self) -> list[dict[str, Any]]:
        """[补齐 Gap-P4] 查看历史计划。"""
        return [p.to_dict() for p in self._historical_plans]

    def revise_current_plan(
        self,
        action: Literal["add", "revise", "delete"],
        subtask_idx: int | None = None,
        subtask_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[补齐 Gap-P3] 修改当前计划。AgentScope PlanNotebook.revise_current_plan() 等价。"""
        plan = self._require_plan()
        if action == "add":
            if subtask_data is None:
                raise ValueError("subtask_data required for add")
            new_task = CompatSubTask(
                name=str(subtask_data.get("name", "")),
                description=str(subtask_data.get("description", "")),
                expected_outcome=str(subtask_data.get("expected_outcome", "")),
            )
            plan.subtasks.append(new_task)
            self._notify_change("revise_add")
            return {"action": "add", "index": len(plan.subtasks) - 1}
        elif action == "revise":
            if subtask_idx is None or subtask_data is None:
                raise ValueError("subtask_idx and subtask_data required for revise")
            self._check_index(plan, subtask_idx)
            task = plan.subtasks[subtask_idx]
            task.description = str(subtask_data.get("description", task.description))
            task.expected_outcome = str(subtask_data.get("expected_outcome", task.expected_outcome))
            self._notify_change("revise_update")
            return {"action": "revise", "index": subtask_idx}
        elif action == "delete":
            if subtask_idx is None:
                raise ValueError("subtask_idx required for delete")
            self._check_index(plan, subtask_idx)
            del plan.subtasks[subtask_idx]
            self._notify_change("revise_delete")
            return {"action": "delete", "index": subtask_idx}
        else:
            raise ValueError(f"invalid action: {action}")

    def generate_hint(self) -> str | None:
        """[补齐 Gap-P7] 生成计划上下文提示。类似 AgentScope DefaultPlanToHint。"""
        if self.current_plan is None:
            return None
        plan = self.current_plan
        lines = [f"<system-hint>", f"Current Plan: {plan.name}"]
        for i, task in enumerate(plan.subtasks):
            lines.append(task.to_oneline_markdown())
        lines.append("</system-hint>")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "historical_plans": [p.to_dict() for p in self._historical_plans],
        }

    def load_dict(self, data: dict[str, Any]) -> None:
        payload = data.get("current_plan")
        if isinstance(payload, dict):
            self.current_plan = CompatPlan.from_dict(payload)
        else:
            self.current_plan = None
        self._historical_plans = [
            CompatPlan.from_dict(p)
            for p in data.get("historical_plans", [])
            if isinstance(p, dict)
        ]

    def _require_plan(self) -> CompatPlan:
        if self.current_plan is None:
            raise ValueError("no active plan; call create_plan first")
        return self.current_plan

    def _check_index(self, plan: CompatPlan, index: int) -> None:
        if not 0 <= index < len(plan.subtasks):
            raise ValueError(f"invalid subtask_idx: {index}")

    def _notify_change(self, action: str) -> None:
        for hook in self._change_hooks:
            try:
                hook(action, self.current_plan)
            except Exception:
                pass


# ===========================================================================
# Capability 4: Tool — 工具系统
# AgentScope: Toolkit + RegisteredToolFunction + ToolResponse(stream)
# DARE:       ITool + ToolManager + ToolGateway + ToolResult
# 基本等价 [E0]，但缺少流式工具结果 [Gap-T1] 和中间件 [Gap-T2]
# ===========================================================================


class _NotebookToolBase(ITool):
    """Shared behavior for compatibility notebook tools."""

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL


class CreatePlanNotebookTool(_NotebookToolBase):
    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "create_plan_notebook"

    @property
    def description(self) -> str:
        return "Create a plan with sequential subtasks."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        name: str,
        description: str,
        expected_outcome: str,
        subtasks: list[dict[str, Any]],
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            output = self._notebook.create_plan(
                name=name,
                description=description,
                expected_outcome=expected_outcome,
                subtasks=subtasks,
            )
            return ToolResult(success=True, output=output)
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class UpdateSubTaskStateTool(_NotebookToolBase):
    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "update_subtask_state"

    @property
    def description(self) -> str:
        return "Update a subtask state to todo/in_progress/abandoned."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        subtask_idx: int,
        state: Literal["todo", "in_progress", "abandoned"],
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            output = self._notebook.update_subtask_state(subtask_idx, state)
            return ToolResult(success=True, output=output)
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class FinishSubTaskTool(_NotebookToolBase):
    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "finish_subtask"

    @property
    def description(self) -> str:
        return "Mark a subtask as done with explicit outcome."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        subtask_idx: int,
        subtask_outcome: str,
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            output = self._notebook.finish_subtask(subtask_idx, subtask_outcome)
            return ToolResult(success=True, output=output)
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class FinishPlanTool(_NotebookToolBase):
    """[补齐 Gap-P2] 标记计划完成/放弃。"""

    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "finish_plan"

    @property
    def description(self) -> str:
        return "Mark the current plan as done or abandoned with an overall outcome."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        state: Literal["done", "abandoned"],
        outcome: str = "",
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            output = self._notebook.finish_plan(state, outcome)
            return ToolResult(success=True, output=output)
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class RevisePlanTool(_NotebookToolBase):
    """[补齐 Gap-P3] 修改当前计划（添加/修改/删除子任务）。"""

    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "revise_current_plan"

    @property
    def description(self) -> str:
        return "Revise the current plan: add, revise, or delete a subtask."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        action: Literal["add", "revise", "delete"],
        subtask_idx: int | None = None,
        subtask_data: dict[str, Any] | None = None,
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            output = self._notebook.revise_current_plan(action, subtask_idx, subtask_data)
            return ToolResult(success=True, output=output)
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class ViewSubTasksTool(_NotebookToolBase):
    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._notebook = notebook

    @property
    def name(self) -> str:
        return "view_subtasks"

    @property
    def description(self) -> str:
        return "View all current subtasks in the notebook."

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        try:
            return ToolResult(success=True, output={"subtasks": self._notebook.view_subtasks()})
        except Exception as exc:
            return ToolResult(success=False, output={}, error=str(exc))


class EchoTool(ITool):
    """Simple utility tool used in the scripted demo flow."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Return the same text payload for demonstration."

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        text: str,
    ) -> ToolResult[dict[str, Any]]:
        _ = run_context
        return ToolResult(success=True, output={"text": text})


class CompatPlanNotebookProvider(IToolProvider):
    """Tool provider exposing notebook-equivalent capabilities.

    比原版增加了 FinishPlanTool [Gap-P2] 和 RevisePlanTool [Gap-P3]。
    """

    def __init__(self, notebook: CompatPlanNotebook) -> None:
        self._tools: list[ITool] = [
            CreatePlanNotebookTool(notebook),
            UpdateSubTaskStateTool(notebook),
            FinishSubTaskTool(notebook),
            FinishPlanTool(notebook),
            RevisePlanTool(notebook),
            ViewSubTasksTool(notebook),
        ]

    def list_tools(self) -> list[ITool]:
        return list(self._tools)


# ===========================================================================
# Capability 12: Session — 状态持久化
# AgentScope: SessionBase + StateModule 协议 + JsonSession/RedisSession
# DARE:       无等价接口 [Gap-S1, Gap-S2]
# ===========================================================================


class JsonSessionBridge:
    """Capability 12: Session 兼容实现。

    等价于 AgentScope JsonSession 的功能子集。

    当前限制（受框架 Gap 影响）：
    - [Gap-S1] 无 StateModule 协议，需手动序列化每个组件
    - [Gap-S2] 无 ISessionStore 接口，此处直接操作文件
    - [Gap-Mem3] InMemorySTM 无 state_dict()，需外部遍历 stm_get()

    框架补齐后，应替换为：
      session_store = JsonSessionStore(save_dir)
      await session_store.save(session_id, user_id,
          memory=agent.stm,      # STM 实现 StateModule
          plan=agent.planner,    # PlannerState 实现 StateModule
          knowledge=agent.knowledge,
      )
    """

    def __init__(self, save_dir: str | Path) -> None:
        self._save_dir = Path(save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)

    def save_session_state(
        self,
        *,
        session_id: str,
        context: Context,
        notebook: CompatPlanNotebook,
        user_id: str = "",
    ) -> None:
        payload = {
            "messages": [self._message_to_dict(message) for message in context.stm_get()],
            "notebook": notebook.to_dict(),
        }
        self._path(session_id, user_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_session_state(
        self,
        *,
        session_id: str,
        context: Context,
        notebook: CompatPlanNotebook,
        user_id: str = "",
        allow_not_exist: bool = True,
    ) -> None:
        path = self._path(session_id, user_id)
        if not path.exists():
            if allow_not_exist:
                return
            raise ValueError(f"session not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        context.stm_clear()
        for item in data.get("messages", []):
            context.stm_add(self._message_from_dict(item))
        notebook.load_dict(data.get("notebook", {}))

    def _path(self, session_id: str, user_id: str) -> Path:
        file_name = f"{user_id}_{session_id}.json" if user_id else f"{session_id}.json"
        return self._save_dir / file_name

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        return {
            "role": message.role,
            "kind": message.kind,
            "text": message.text,
            "attachments": [
                {
                    "kind": attachment.kind,
                    "uri": attachment.uri,
                    "mime_type": attachment.mime_type,
                    "filename": attachment.filename,
                    "metadata": dict(attachment.metadata),
                }
                for attachment in message.attachments
            ],
            "data": dict(message.data) if isinstance(message.data, dict) else None,
            "name": message.name,
            "metadata": dict(message.metadata),
        }

    def _message_from_dict(self, data: dict[str, Any]) -> Message:
        return Message(
            role=str(data.get("role", "user")),
            kind=str(data.get("kind", "chat")),
            text=data.get("text"),
            attachments=data.get("attachments", []),
            data=data.get("data"),
            name=data.get("name"),
            metadata=dict(data.get("metadata", {})),
        )


# ===========================================================================
# Capability 11: HttpStatefulClient — 有状态 MCP HTTP 客户端
# AgentScope: HttpStatefulClient(connect/close/list_tools/get_callable_function)
# DARE:       MCPClient + HTTPTransport（功能等价，无上层 facade）[Gap-H1]
# ===========================================================================


class HttpStatefulClientShim:
    """Capability 11: HttpStatefulClient 兼容 facade。

    在 DARE 的 MCPClient + HTTPTransport 之上提供 AgentScope 风格的 API。

    当前限制：
    - [Gap-H2] 无自动重连：连接断开后不自动恢复
    - [Gap-H3] list_tools() 每次都发网络请求，不缓存
    """

    def __init__(
        self,
        *,
        name: str,
        transport: Literal["streamable_http", "sse"],
        url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        enable_notifications: bool = False,
    ) -> None:
        if transport not in {"streamable_http", "sse"}:
            raise ValueError(f"unsupported transport: {transport}")
        self.name = name
        self.transport = transport
        self._http_transport = HTTPTransport(
            url=url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            enable_notifications=enable_notifications,
        )
        self._client = MCPClient(name, self._http_transport, transport_type=transport)
        self.is_connected = False
        self._cached_tools: list[ITool] | None = None  # [补齐 Gap-H3]

    async def connect(self) -> None:
        await self._client.connect()
        self.is_connected = True
        self._cached_tools = None

    async def close(self) -> None:
        await self._client.disconnect()
        self.is_connected = False
        self._cached_tools = None

    async def list_tools(self, use_cache: bool = True) -> list[ITool]:
        """列出可用工具。[补齐 Gap-H3] 支持缓存。"""
        if use_cache and self._cached_tools is not None:
            return self._cached_tools
        tools = await self._client.list_tools()
        self._cached_tools = tools
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        return await self._client.call_tool(tool_name, arguments)


# ===========================================================================
# Capability 10: Knowledge — 知识检索 (RAG)
# AgentScope: KnowledgeBase.retrieve(query, limit, score_threshold) — 向量语义检索
# DARE:       IKnowledge.get(query) — rawdata(子串) + vector(embedding)
# 基本等价 [E0]，但 vector 路径需要 EmbeddingAdapter [Gap-K1]
# ===========================================================================

# Knowledge 直接使用 dare_framework.knowledge.create_knowledge()，无需额外兼容层。
# 差距在框架层：
# - [Gap-K1] 缺 OpenRouterEmbeddingAdapter，vector knowledge 需手动配置 OpenAI 的 embedding
# - [Gap-K2] IKnowledge.get() 是同步方法，VectorKnowledge 内部用 _run_async() 绕过
# - [Gap-K4] 无 score_threshold 参数


# ===========================================================================
# Demo Builder — 构建完整兼容 agent
# ===========================================================================


@dataclass
class DemoBundle:
    """Return object for tests and CLI."""

    agent: Any
    notebook: CompatPlanNotebook
    model: IModelAdapter
    session: JsonSessionBridge
    formatter: CompatTruncatedFormatter
    knowledge: Any
    memory_wrapper: CompatMemoryWrapper | None = None


async def build_single_agent_demo(
    *,
    workspace_dir: Path,
    model_adapter: IModelAdapter | None = None,
    max_prompt_chars: int = 1200,
    agent_channel: AgentChannel | None = None,
) -> DemoBundle:
    """Build the single-agent compatibility demo.

    This function demonstrates how to wire together all 12 AgentScope-equivalent
    capabilities using DARE framework primitives + compatibility shims.

    构建流程对应 AgentScope 的:
    ```python
    agent = ReActAgent(
        name="example-10-agent",
        sys_prompt="...",
        model=model,                      # ChatModelBase
        memory=InMemoryMemory(),           # InMemoryMemory
        formatter=TruncatedFormatter(...), # TruncatedFormatterBase
        toolkit=toolkit,                   # Toolkit
        knowledge=[knowledge],             # KnowledgeBase
        plan_notebook=PlanNotebook(),       # PlanNoteBook
    )
    session = JsonSession(save_dir=...)    # Session
    ```
    """

    workspace_dir.mkdir(parents=True, exist_ok=True)
    user_dir = workspace_dir / "user"
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config(
        workspace_dir=str(workspace_dir),
        user_dir=str(user_dir),
    )
    if model_adapter is None:
        raise ValueError("model_adapter is required for build_single_agent_demo")

    # Capability 9: TruncatedFormatterBase
    formatter = CompatTruncatedFormatter(max_chars=max_prompt_chars)
    # Capability 6: ChatModelBase (with formatter wrapping)
    model = CompatFormattedModelAdapter(model_adapter, formatter)
    # Capability 7+8: PlanNoteBook + SubTask
    notebook = CompatPlanNotebook()
    provider = CompatPlanNotebookProvider(notebook)

    # Capability 10: Knowledge (rawdata mode — vector mode needs Gap-K1)
    knowledge = create_knowledge({"type": "rawdata", "storage": "in_memory"})
    if knowledge is None:
        raise RuntimeError("failed to create in-memory knowledge")
    knowledge.add(
        "DARE Framework 使用 ReactAgentBuilder、ToolGateway 和 Context 来执行 ReAct 循环。",
        metadata={"source": "example-10"},
    )

    # Capability 1: ReActAgent
    builder = (
        BaseAgent.react_agent_builder("example-10-agent")
        .with_model(model)
        .with_config(config)
        .with_knowledge(knowledge)
        .add_tool_provider(provider)
        .add_tools(EchoTool())
    )
    if agent_channel is not None:
        builder = builder.with_agent_channel(agent_channel)

    agent = await builder.build()

    # Capability 12: Session
    session = JsonSessionBridge(workspace_dir / "sessions")

    # Capability 5: InMemoryMemory (enhanced wrapper)
    memory_wrapper = CompatMemoryWrapper(agent.context)

    return DemoBundle(
        agent=agent,
        notebook=notebook,
        model=model,
        session=session,
        formatter=formatter,
        knowledge=knowledge,
        memory_wrapper=memory_wrapper,
    )


__all__ = [
    "CompatFormattedModelAdapter",
    "CompatMemoryWrapper",
    "CompatMsg",
    "CompatPlan",
    "CompatPlanNotebook",
    "CompatPlanNotebookProvider",
    "CompatSubTask",
    "CompatTruncatedFormatter",
    "ContentBlock",
    "DemoBundle",
    "FinishPlanTool",
    "FormattedPrompt",
    "HttpStatefulClientShim",
    "ISessionStore",
    "JsonSessionBridge",
    "MessageTag",
    "RevisePlanTool",
    "StateModule",
    "TextBlock",
    "ThinkingBlock",
    "build_single_agent_demo",
]
