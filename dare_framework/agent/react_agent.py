"""ReactAgent - agent with ReAct tool loop (Reason → Act → Observe).

When the model returns tool_calls, this agent executes them, adds tool results
to context, and calls the model again until the model returns a final text response.
"""

from __future__ import annotations

import math
import json
from typing import Any

# ANSI: plan-agent 红字，sub-agent 绿字，工具名紫字，context 列表黄字
_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_PURPLE = "\033[35m"
_ANSI_RESET = "\033[0m"


def _agent_color(name: str) -> str:
    """根据 agent 名称返回 ANSI 颜色码。"""
    if name == "plan-agent":
        return _ANSI_RED
    if name.startswith("sub_agent"):
        return _ANSI_GREEN
    return _ANSI_RESET


def _colored_print(agent_name: str, msg: str, tool_name: str | None = None) -> None:
    """带颜色的 agent 日志打印。若提供 tool_name，则工具名用紫色高亮。"""
    color = _agent_color(agent_name)
    if tool_name:
        msg = msg.replace(tool_name, f"{_ANSI_PURPLE}{tool_name}{_ANSI_RESET}{color}", 1)
    print(f"{color}{msg}{_ANSI_RESET}", flush=True)


from dare_framework.agent._internal.output_normalizer import build_output_envelope
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import Context, Message, SmartContext
from dare_framework.context.types import MessageKind, MessageMark, MessageRole
from dare_framework.context.manage_context import MANAGE_CONTEXT_TOOL_NAME


def _print_tools_sent_to_llm(agent_name: str, tools: list[Any]) -> None:
    """打印发给 LLM 的 tools 完整信息（黄字）。"""
    if not tools:
        return
    api_tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]
    blob = json.dumps(api_tools, indent=2, ensure_ascii=False)
    lines = [f"[{agent_name}] Tools 发给 LLM ({len(tools)} 个):", "---", blob, "---"]
    print(f"{_ANSI_YELLOW}{chr(10).join(lines)}{_ANSI_RESET}", flush=True)


# TEMPORARY 消息打印时截断，避免过长
_TEMP_MSG_MAX_CHARS = 400


def _print_context_list(
    agent_name: str, messages: list[Message], *, sys_prompt_brief: bool = False
) -> None:
    """打印与发给 LLM 完全一致的消息列表（黄字）：role + content。
    sys_prompt_brief=True 时，sys_prompt 仅打印简略版。
    mark=TEMPORARY 的消息过长时截断，避免刷屏。"""
    lines = [f"[{agent_name}] 发给 LLM 的 Context ({len(messages)} msgs)，格式与 API 一致:"]
    for i, m in enumerate(messages):
        mid = getattr(m, "id", None)
        mmark = getattr(m, "mark", MessageMark.TEMPORARY)
        content = m.text or ""
        if sys_prompt_brief and mid == "sys_prompt":
            content = f"[sys_prompt 略，首轮已打印完整] ({len(m.text or '')} chars)"
        elif mmark == MessageMark.TEMPORARY and len(content) > _TEMP_MSG_MAX_CHARS:
            content = content[:_TEMP_MSG_MAX_CHARS] + f"\n... [截断，共 {len(content)} chars]"
        lines.append(f"--- Message {i+1} role={m.role} ---")
        lines.append(content)
        lines.append("")
    print(f"{_ANSI_YELLOW}{chr(10).join(lines)}{_ANSI_RESET}", flush=True)


from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.plan.types import Envelope
from dare_framework.plan.types import RunResult
from dare_framework.tool import IToolGateway, IToolProvider
from dare_framework.transport.kernel import AgentChannel
from dare_framework.transport.types import EnvelopeKind, MessagePayload, TransportEnvelope, new_envelope_id


class ReactAgent(BaseAgent):
    """Chat agent that executes tool calls in a ReAct loop.

    当 context 是 SmartContext 且配置挂载了 manage_context 工具时，
    会启用 SmartContext 能力（CORE / task_complete / manage_context 约束）；
    否则退化为基础 ReAct 循环。
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: Context,
        tool_gateway: IToolGateway,
        plan_provider: IToolProvider | None = None,
        max_tool_rounds: int = 10,
        agent_channel: AgentChannel | None = None,
    ) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self._model = model
        self._max_tool_rounds = max_tool_rounds
        self._context = context
        self._tool_gateway = tool_gateway
        self._plan_provider = plan_provider
        self._context.set_tool_gateway(self._tool_gateway)

        # 运行时检测是否可以启用 SmartContext 能力
        self._smart_context_enabled = isinstance(context, SmartContext)

    @property
    def context(self) -> Context:
        return self._context

    @property
    def plan_provider(self) -> IToolProvider | None:
        """Return optional mounted plan provider (if configured by builder)."""
        return self._plan_provider

    async def execute(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """根据当前 context 类型与配置，选择基础 ReAct 或 SmartContext 增强模式。"""
        if self._smart_context_enabled:
            return await self._execute_with_smart_context(task, transport=transport)
        return await self._execute_basic(task, transport=transport)

    async def _execute_basic(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """原始基础 ReAct 循环实现。"""
        self._context.stm_add(task)

        gateway = self._tool_gateway

        last_tool_signature: tuple[str, ...] | None = None
        repeated_tool_rounds = 0
        latest_usage: dict[str, Any] | None = None

        for round_idx in range(self._max_tool_rounds):
            print(f"[{self.name}] Round {round_idx + 1}/{self._max_tool_rounds}: 调用模型中...", flush=True)
            assembled = await self._context.assemble_for_model()
            messages = self._build_model_messages(assembled)

            model_input = ModelInput(
                messages=messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )
            response = await self._model.generate(model_input)
            usage = response.usage if isinstance(response.usage, dict) and response.usage else None
            if usage is not None:
                usage_total_tokens = _usage_total_tokens(usage)
                # Keep the latest meaningful usage totals. Some adapters emit
                # placeholder zero usage in later rounds and should not erase
                # previously reported non-zero usage.
                if usage_total_tokens > 0 or latest_usage is None:
                    latest_usage = usage
            n_tools = len(response.tool_calls) if response.tool_calls else 0
            print(f"[{self.name}] 模型返回, tool_calls={n_tools}", flush=True)
            thinking_content = (response.thinking_content or "").strip()
            if thinking_content:
                await self._emit_transport_message(
                    transport=transport,
                    message_kind=MessageKind.THINKING,
                    text=thinking_content,
                    data={"target": "model"},
                )

            if usage is not None:
                tokens = _usage_total_tokens(usage)
                if tokens:
                    self._context.budget_use("tokens", tokens)
            self._context.budget_check()

            if not response.tool_calls:
                final_text = (response.content or "").strip()
                if not final_text:
                    final_text = "模型未返回可显示的文本回复。请重试，或明确要求先调用 ask_user 再继续。"
                assistant_message = Message(role="assistant", text=final_text)
                self._context.stm_add(assistant_message)
                await self._emit_terminal_transport_message(
                    transport=transport,
                    output=final_text,
                )
                output = build_output_envelope(
                    final_text,
                    usage=latest_usage,
                )
                return RunResult(
                    success=True,
                    output=output,
                    output_text=output["content"],
                )

            current_signature = _tool_calls_signature(response.tool_calls)
            if current_signature and current_signature == last_tool_signature:
                repeated_tool_rounds += 1
            else:
                repeated_tool_rounds = 1
            last_tool_signature = current_signature

            if repeated_tool_rounds >= 3:
                loop_guard = "模型连续重复调用相同工具，已停止自动循环。请换一种描述，或明确要求先调用 ask_user 再继续。"
                self._context.stm_add(Message(role="assistant", text=loop_guard))
                await self._emit_terminal_transport_message(
                    transport=transport,
                    output=loop_guard,
                )
                output = build_output_envelope(loop_guard, usage=latest_usage)
                return RunResult(success=True, output=output, output_text=output["content"])

            assistant_msg = Message(
                role="assistant",
                kind="tool_call",
                text=response.content or "",
                data={"tool_calls": response.tool_calls},
            )
            self._context.stm_add(assistant_msg)

            envelope = Envelope()
            for tool_call in response.tool_calls:
                name = tool_call.get("name", "")
                tool_call_id = tool_call.get("id", "")
                params = _normalize_tool_args(tool_call.get("arguments", {}))
                await self._emit_transport_message(
                    transport=transport,
                    message_kind=MessageKind.TOOL_CALL,
                    text=name or "tool_call",
                    data={
                        "target": name or "tool_call",
                        "id": tool_call_id,
                        "name": name,
                        "arguments": params,
                    },
                )
                # 打印工具调用信息：名称、参数
                params_str = json.dumps(params, ensure_ascii=False)
                params_preview = params_str[:300] + ("..." if len(params_str) > 300 else "")
                print(f"[{self.name}] 工具调用: {name} | id={tool_call_id or '-'} | args={params_preview}", flush=True)

                try:
                    # 关键修复：将当前 Context 传递给 ToolGateway，使工具能看到 config/workspace_dir
                    result = await gateway.invoke(name, envelope=envelope, context=self._context, **params)
                except Exception as exc:
                    await self._emit_transport_error(
                        transport=transport,
                        target=name or "tool_call",
                        code="TOOL_CALL_FAILED",
                        reason=str(exc).strip() or exc.__class__.__name__,
                    )
                    result = type("R", (), {"success": False, "output": {}, "error": str(exc)})()

                success = getattr(result, "success", False)
                output = getattr(result, "output", {})
                # 打印工具执行结果摘要
                out_preview = _preview_output(output)
                print(f"[{self.name}] 工具结果: {name} | success={success} | {out_preview}", flush=True)
                error = getattr(result, "error", "") or ""
                await self._emit_transport_message(
                    transport=transport,
                    message_kind=MessageKind.TOOL_RESULT,
                    text=name or "tool_result",
                    data={
                        "target": name or "tool_result",
                        "id": tool_call_id,
                        "name": name,
                        "success": bool(success),
                        "output": output,
                        "error": error,
                    },
                )

                tool_content = json.dumps(
                    {"success": success, "output": output, "error": error} if not success
                    else {"success": True, "output": output},
                    ensure_ascii=False,
                    default=str,
                )
                tool_msg = Message(
                    role="tool",
                    kind="tool_result",
                    name=tool_call_id or name,
                    text=tool_content,
                    data={
                        "tool_call_id": tool_call_id or name,
                        "tool_name": name,
                        "success": bool(success),
                        "output": output,
                        "error": error,
                    },
                )
                self._context.stm_add(tool_msg)

        final_message = "模型在工具循环中未收敛（达到最大轮次）。请缩小范围，或明确要求先调用 ask_user 再继续。"
        await self._emit_terminal_transport_message(
            transport=transport,
            output=final_message,
        )
        output = build_output_envelope(final_message, usage=latest_usage)
        return RunResult(
            success=True,
            output=output,
            output_text=output["content"],
        )

    async def _execute_with_smart_context(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """启用 SmartContext 能力的 ReAct 循环。

        需要：
        - context 为 SmartContext 实例；
        - tools 中存在 manage_context 工具（由 ReactAgentBuilder 自动挂载）。
        """
        if not isinstance(self._context, SmartContext):
            # 防御性降级：即使标记为 smart 也要保证类型安全
            return await self._execute_basic(task, transport=transport)

        _ = transport
        source_user_message = task
        user_message = Message(
            role=source_user_message.role,
            kind=source_user_message.kind,
            text=source_user_message.text,
            attachments=list(source_user_message.attachments),
            data=dict(source_user_message.data) if isinstance(source_user_message.data, dict) else None,
            metadata=dict(source_user_message.metadata),
            mark=MessageMark.IMMUTABLE,
            id="user_task",  # 用户/上层任务需求，manage_context 判断 task_complete 须对照此消息
        )
        self._context.stm_add(user_message)

        # 临时信息，注入 llm，但是不放入 stm_add，用完即失效
        self._next_round_reflection_prompt: Message | None = None

        gateway = self._tool_gateway

        # 循环外一次性确定：agent 是否挂载了 manage_context（不随轮次变化）
        assembled_once = self._context.assemble()
        tools_list = getattr(assembled_once, "tools", None) or []
        has_manage_context_tool = any(
            getattr(t, "id", "") == MANAGE_CONTEXT_TOOL_NAME or getattr(t, "name", "") == MANAGE_CONTEXT_TOOL_NAME
            for t in tools_list
        )

        # 进入 agent 即注入：首轮指导调用 manage_context 根据任务初始化 context（仅传入一次，不写 STM）
        if has_manage_context_tool:
            self._next_round_reflection_prompt = Message(
                role="assistant",
                text="【提示】请先调用 manage_context 根据任务初始化 context 状态。",
            )

        # Agent 工程约束：执行其它 tool 之前，必须至少执行过一次 manage_context
        manage_context_has_run = False

        for round_idx in range(self._max_tool_rounds):
            _colored_print(self.name, f"[{self.name}] Round {round_idx + 1}/{self._max_tool_rounds}: 调用模型中...")
            assembled = await self._context.assemble_for_model()
            messages = list(assembled.messages)
            prompt_def = getattr(assembled, "sys_prompt", None)
            sys_prompt_message = (
                Message(
                    role=prompt_def.role,
                    text=prompt_def.content,
                    name=prompt_def.name,
                    metadata=dict(prompt_def.metadata),
                    mark=MessageMark.IMMUTABLE,
                    id="sys_prompt",
                )
                if prompt_def is not None
                else None
            )
            messages = self._context.order_messages_for_llm(messages, sys_prompt_message)

            # 注入 _next_round_reflection_prompt：普通工具轮后提示，仅本次 LLM 调用传入，不写 STM
            injected_reflection_prompt = self._next_round_reflection_prompt
            if self._next_round_reflection_prompt is not None:
                messages.append(self._next_round_reflection_prompt)
                self._next_round_reflection_prompt = None

            # Inject critical_block from plan_provider (maintained by plan tools)
            # Disabled: skip injection to observe plan agent behavior without it
            if False and self._plan_provider is not None:
                state = getattr(self._plan_provider, "state", None)
                critical_block = getattr(state, "critical_block", "") if state else ""
                if critical_block:
                    _colored_print(self.name, "\n--- [Plan State] (injected) ---\n" + critical_block + "\n---\n")
                    n_front = sum(1 for m in messages if getattr(m, "id", None) in ("core", "task_complete"))
                    messages.insert(n_front, Message(role="system", text=critical_block, name="plan_state"))

            _print_context_list(self.name, messages, sys_prompt_brief=(round_idx > 0))
            if round_idx == 0 and assembled.tools:
                _print_tools_sent_to_llm(self.name, assembled.tools)

            model_input = ModelInput(
                messages=messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )
            response = await self._model.generate(model_input)
            n_tools = len(response.tool_calls) if response.tool_calls else 0
            _colored_print(self.name, f"[{self.name}] 模型返回, tool_calls={n_tools}")

            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                if tokens:
                    self._context.budget_use("tokens", tokens)
            self._context.budget_check()

            if not response.tool_calls:
                final_text = (response.content or "").strip()
                if not final_text:
                    final_text = "模型未返回可显示的文本回复。\n"

                if has_manage_context_tool:
                    task_complete = self._context.get_task_complete()
                    if not task_complete:
                        self._next_round_reflection_prompt = Message(
                            role="assistant",
                            text=final_text + "任务未完成，请先调用 manage_context 仔细审视任务是否完成。",
                        )
                        continue

                assistant_message = Message(role="assistant", text=final_text)
                self._context.stm_add(assistant_message)
                return RunResult(
                    success=True,
                    output=final_text,
                    output_text=final_text,
                )

            # 将本轮带有 tool_calls 的 assistant 消息写入 STM，
            # 供 OpenRouter/OpenAI 风格的 tool calling 正确关联后续 tool 结果（tool_call_id 必须能在对话中找到）。
            tool_names = [str(t.get("name", "")) for t in response.tool_calls if isinstance(t, dict)]
            has_manage_context = MANAGE_CONTEXT_TOOL_NAME in tool_names

            envelope = Envelope()
            manage_context_succeeded = False

            if has_manage_context_tool and has_manage_context:
                # 只执行第一个 manage_context，其他工具本轮不执行
                mc_calls = [
                    t for t in response.tool_calls
                    if isinstance(t, dict) and t.get("name") == MANAGE_CONTEXT_TOOL_NAME
                ]
                tool_calls_to_run = mc_calls[:1] if mc_calls else []
                for tool_call in tool_calls_to_run:
                    name = tool_call.get("name", "")
                    tool_call_id = tool_call.get("id", "") or tool_call.get("name", "")
                    params = _normalize_tool_args(tool_call.get("arguments", {}))
                    params_str = json.dumps(params, ensure_ascii=False)
                    params_preview = params_str[:800] + ("..." if len(params_str) > 800 else "")
                    _colored_print(
                        self.name,
                        f"[{self.name}] 工具调用: {name} | id={tool_call_id or '-'} | args={params_preview}",
                        tool_name=name,
                    )
                    try:
                        result = await gateway.invoke(name, envelope=envelope, context=self._context, **params)
                    except Exception as exc:
                        result = type("R", (), {"success": False, "output": {}, "error": str(exc)})()
                    success = getattr(result, "success", False)
                    output = getattr(result, "output", {})
                    out_preview = _preview_output(output)
                    _colored_print(
                        self.name,
                        f"[{self.name}] 工具结果: {name} | success={success} | {out_preview}",
                        tool_name=name,
                    )

                    if success:
                        manage_context_succeeded = True
                        self._next_round_reflection_prompt = Message(
                            role="assistant",
                            text="已调用manage_context更新context。可参考context中的CORE状态和USER_TASK继续执行任务。\n",
                        )
                    else:
                        error = getattr(result, "error", "") or ""
                        error += "manage_context执行失败，请重试manage_context。"
                        self._next_round_reflection_prompt = Message(
                            role="assistant",
                            text=error,
                        )
            elif has_manage_context_tool and not manage_context_has_run:
                self._next_round_reflection_prompt = Message(
                    role="assistant",
                    text="还未调用manage_context来更新context状态，请先调用manage_context去更新context状态...\n",
                )
            else:
                assistant_msg = Message(
                    role="assistant",
                    kind="tool_call",
                    text=response.content or "",
                    data={"tool_calls": response.tool_calls},
                )
                self._context.stm_add(assistant_msg)

                tool_calls_to_run = [t for t in response.tool_calls if isinstance(t, dict)]
                for tool_call in tool_calls_to_run:
                    name = tool_call.get("name", "")
                    tool_call_id = tool_call.get("id", "") or tool_call.get("name", "")
                    params = _normalize_tool_args(tool_call.get("arguments", {}))
                    params_str = json.dumps(params, ensure_ascii=False)
                    params_preview = params_str[:800] + ("..." if len(params_str) > 800 else "")
                    _colored_print(
                        self.name,
                        f"[{self.name}] 工具调用: {name} | id={tool_call_id or '-'} | args={params_preview}",
                        tool_name=name,
                    )
                    try:
                        result = await gateway.invoke(name, envelope=envelope, context=self._context, **params)
                    except Exception as exc:
                        result = type("R", (), {"success": False, "output": {}, "error": str(exc)})()
                    success = getattr(result, "success", False)
                    output = getattr(result, "output", {})
                    out_preview = _preview_output(output)
                    _colored_print(
                        self.name,
                        f"[{self.name}] 工具结果: {name} | success={success} | {out_preview}",
                        tool_name=name,
                    )
                    error = getattr(result, "error", "") or ""
                    tool_content = json.dumps(
                        {"success": success, "output": output, "error": error} if not success
                        else {"success": True, "output": output},
                        ensure_ascii=False,
                        default=str,
                    )
                    tool_msg = Message(
                        role="tool",
                        kind="tool_result",
                        name=tool_call_id or name,
                        text=tool_content,
                        data={
                            "tool_call_id": tool_call_id or name,
                            "tool_name": name,
                            "success": bool(success),
                            "output": output,
                            "error": error,
                        },
                    )
                    self._context.stm_add(tool_msg)
                self._next_round_reflection_prompt = Message(
                    role="assistant",
                    text="工具调用结束(或成功或失败)，请调用 manage_context反思当前进展、更新context状态。",
                )
            if manage_context_succeeded:
                manage_context_has_run = True
            else:
                manage_context_has_run = False

        final_message = "模型在工具循环中未收敛（达到最大轮次）。请缩小范围，或明确要求先调用 ask_user 再继续。"
        return RunResult(
            success=True,
            output=final_message,
            output_text=final_message,
        )

    def _build_model_messages(self, assembled: Any) -> list[Message]:
        """Build model-facing messages including system prompt and plan state injection."""
        messages = list(assembled.messages)
        prompt_def = getattr(assembled, "sys_prompt", None)
        if prompt_def is not None:
            messages = [
                Message(
                    role=prompt_def.role,
                    text=prompt_def.content,
                    name=prompt_def.name,
                    metadata=dict(prompt_def.metadata),
                ),
                *messages,
            ]
        if self._plan_provider is not None:
            state = getattr(self._plan_provider, "state", None)
            critical_block = getattr(state, "critical_block", "") if state else ""
            if critical_block:
                print("\n--- [Plan State] (injected) ---\n" + critical_block + "\n---\n", flush=True)
                messages.insert(
                    1,
                    Message(role="system", text=critical_block, name="plan_state"),
                )
        return messages

    async def _emit_terminal_transport_message(
        self,
        *,
        transport: AgentChannel | None,
        output: str,
    ) -> None:
        """Emit terminal MESSAGE for direct execute() transport calls."""
        # BaseAgent emits terminal RESULT envelopes in transport-loop execution.
        # Avoid emitting duplicate terminal MESSAGE events in that path.
        if self._is_transport_loop_execution(transport=transport):
            return
        await self._emit_transport_message(
            transport=transport,
            message_kind=MessageKind.CHAT,
            text=output,
            data={"target": "prompt", "success": True, "output": output},
        )

    async def _emit_transport_message(
        self,
        *,
        transport: AgentChannel | None,
        message_kind: MessageKind,
        text: str | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit a typed message payload to transport when available."""
        if transport is None:
            return
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id=new_envelope_id(),
                role=MessageRole.ASSISTANT,
                message_kind=message_kind,
                text=text,
                data=data,
            ),
        )
        try:
            await transport.send(envelope)
        except Exception:
            self._logger.exception("react agent transport message emission failed")

    async def _emit_transport_error(
        self,
        *,
        transport: AgentChannel | None,
        target: str,
        code: str,
        reason: str,
    ) -> None:
        """Emit a canonical error payload to transport when available."""
        if transport is None:
            return
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.MESSAGE,
            payload=MessagePayload(
                id=new_envelope_id(),
                role=MessageRole.ASSISTANT,
                message_kind=MessageKind.SUMMARY,
                text=reason,
                data={
                    "success": False,
                    "target": target,
                    "code": code,
                    "reason": reason,
                },
            ),
        )
        try:
            await transport.send(envelope)
        except Exception:
            self._logger.exception("react agent transport error emission failed")


def _preview_output(output: Any, max_len: int = 120) -> str:
    """生成 output 的简短预览，用于日志打印。"""
    if output is None:
        return "output=None"
    if isinstance(output, dict):
        # 常见字段优先展示
        for key in ("content", "path", "matches", "paths"):
            if key in output:
                val = output[key]
                if isinstance(val, str):
                    preview = val[:max_len] + ("..." if len(val) > max_len else "")
                elif isinstance(val, list):
                    preview = f"list[{len(val)}]"
                else:
                    preview = str(val)[:max_len]
                return f"{key}={preview}"
        serialized = json.dumps(output, ensure_ascii=False, default=str)
        s = serialized[:max_len]
        return s + ("..." if len(serialized) > max_len else "")
    s = str(output)[:max_len]
    return s + ("..." if len(str(output)) > max_len else "")


def _normalize_tool_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, str):
        try:
            decoded = json.loads(raw_args) if raw_args.strip() else {}
        except json.JSONDecodeError:
            decoded = {}
        return decoded if isinstance(decoded, dict) else {}
    if isinstance(raw_args, dict):
        return raw_args
    return {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _usage_total_tokens(usage: dict[str, Any]) -> int:
    total_tokens = usage.get("total_tokens")
    if total_tokens is None:
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        return _safe_int(input_tokens) + _safe_int(output_tokens)
    return _safe_int(total_tokens)


def _tool_calls_signature(tool_calls: list[dict[str, Any]]) -> tuple[str, ...]:
    signature: list[str] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        name = str(tool_call.get("name", ""))
        args = _normalize_tool_args(tool_call.get("arguments", {}))
        args_key = json.dumps(args, ensure_ascii=False, sort_keys=True)
        signature.append(f"{name}:{args_key}")
    return tuple(signature)


__all__ = ["ReactAgent"]
