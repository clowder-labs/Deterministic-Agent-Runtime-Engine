"""Execute-loop orchestration helpers for DareAgent.

This module isolates Layer-4 execution control flow from the DareAgent facade.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol
from uuid import uuid4

from dare_framework.context import Message
from dare_framework.hook.types import HookDecision, HookPhase
from dare_framework.model import ModelInput
from dare_framework.plan.types import ToolLoopRequest


class ExecuteEngineAgent(Protocol):
    """Minimal DareAgent contract required by execute-loop execution."""

    _context: Any
    _execution_mode: str
    _exec_ctl: Any
    _max_tool_iterations: int
    _model: Any

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    async def _capability_index(self) -> dict[str, Any]: ...

    async def _run_tool_loop(
        self,
        request: Any,
        *,
        transport: Any | None,
        tool_name: str,
        tool_call_id: str,
        descriptor: Any | None = None,
    ) -> dict[str, Any]: ...

    async def _run_step_driven_execute_loop(
        self,
        plan: Any,
        execute_start: float,
        *,
        transport: Any | None = None,
    ) -> dict[str, Any]: ...

    async def _finalize_execute(self, start_time: float, result: dict[str, Any]) -> dict[str, Any]: ...

    def _apply_context_patch(self, assembled: Any, dispatch: Any) -> tuple[list[Any], list[Any], dict[str, Any]]: ...

    def _apply_model_input_patch(self, model_input: ModelInput, dispatch: Any) -> ModelInput: ...

    def _context_stats(self, messages: list[Any], tools_count: int) -> dict[str, int]: ...

    def _log(self, message: str) -> None: ...

    def _log_model_messages(self, messages: list[Any], *, stage: str) -> None: ...

    def _poll_or_raise(self) -> None: ...

    def _record_token_usage(self, usage: dict[str, Any] | None) -> None: ...

    def _total_tokens_from_usage(self, usage: dict[str, Any]) -> int: ...

    def _budget_stats(self) -> dict[str, Any]: ...

    def _is_plan_tool_call(self, name: str | None, descriptor: Any | None) -> bool: ...

    def _is_skill_tool_call(self, descriptor: Any | None) -> bool: ...

    def _mount_skill_from_result(self, output: Any) -> None: ...


async def run_execute_loop(
    agent: ExecuteEngineAgent,
    plan: Any,
    *,
    transport: Any | None = None,
) -> dict[str, Any]:
    """Run the Layer-4 execute loop."""
    agent._log("Starting execute loop")
    execute_start = time.perf_counter()
    await agent._emit_hook(HookPhase.BEFORE_EXECUTE, {
        "plan_present": plan is not None,
    })
    if agent._execution_mode == "step_driven":
        return await agent._run_step_driven_execute_loop(
            plan,
            execute_start,
            transport=transport,
        )
    agent._context.budget_check()

    before_context_dispatch = await agent._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
    assembled = agent._context.assemble()
    assembled_messages, assembled_tools, assembled_metadata = agent._apply_context_patch(
        assembled,
        before_context_dispatch,
    )
    await agent._emit_hook(
        HookPhase.AFTER_CONTEXT_ASSEMBLE,
        {
            **agent._context_stats(assembled_messages, len(assembled_tools)),
            "budget_stats": agent._budget_stats(),
        },
    )

    model_input = ModelInput(
        messages=assembled_messages,
        tools=assembled_tools,
        metadata=assembled_metadata,
    )

    outputs: list[Any] = []
    errors: list[str] = []

    for iteration in range(agent._max_tool_iterations):
        agent._context.budget_check()

        if agent._exec_ctl is not None:
            agent._poll_or_raise()

        agent._log(f"Execute iteration {iteration + 1}/{agent._max_tool_iterations}")
        agent._log_model_messages(model_input.messages, stage=f"execute:{iteration + 1}")
        before_model_dispatch = await agent._emit_hook(HookPhase.BEFORE_MODEL, {
            "iteration": iteration + 1,
            "model_name": getattr(agent._model, "name", None),
            "model_input": model_input,
        })
        if before_model_dispatch.decision in {HookDecision.BLOCK, HookDecision.ASK}:
            policy_error = (
                "model invocation requires hook approval"
                if before_model_dispatch.decision is HookDecision.ASK
                else "model invocation denied by hook policy"
            )
            errors.append(policy_error)
            return await agent._finalize_execute(
                execute_start,
                {"success": False, "outputs": outputs, "errors": errors},
            )
        model_input = agent._apply_model_input_patch(model_input, before_model_dispatch)
        model_start = time.perf_counter()
        response = await agent._model.generate(model_input)
        model_latency_ms = (time.perf_counter() - model_start) * 1000.0

        if response.usage:
            agent._record_token_usage(response.usage)
            total_tokens = agent._total_tokens_from_usage(response.usage)
            if total_tokens:
                agent._context.budget_use("tokens", total_tokens)

        if response.content:
            content_preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
            agent._log(f"LLM Response: {content_preview}")
        agent._log(f"Tool calls: {len(response.tool_calls)}")

        await agent._log_event("model.response", {
            "iteration": iteration + 1,
            "has_tool_calls": bool(response.tool_calls),
        })
        await agent._emit_hook(HookPhase.AFTER_MODEL, {
            "iteration": iteration + 1,
            "model_name": getattr(agent._model, "name", None),
            "has_tool_calls": bool(response.tool_calls),
            "model_usage": response.usage or {},
            "duration_ms": model_latency_ms,
            "budget_stats": agent._budget_stats(),
            "model_output": {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "metadata": response.metadata,
            },
        })

        if not response.tool_calls:
            assistant_message = Message(role="assistant", text=response.content)
            agent._context.stm_add(assistant_message)

            outputs.append({"content": response.content})
            return await agent._finalize_execute(execute_start, {
                "success": True,
                "outputs": outputs,
                "errors": errors,
            })

        capability_index = await agent._capability_index() if response.tool_calls else {}

        assistant_msg = Message(
            role="assistant",
            kind="tool_call" if response.tool_calls else "chat",
            text=response.content or "",
            data={"tool_calls": response.tool_calls} if response.tool_calls else None,
        )
        agent._context.stm_add(assistant_msg)

        for tool_call in response.tool_calls:
            name = tool_call.get("name") or ""
            capability_id = tool_call.get("capability_id") or name
            tool_call_id = tool_call.get("id") or f"{capability_id}_{iteration + 1}_{uuid4().hex[:6]}"
            descriptor = capability_index.get(capability_id) or capability_index.get(name)

            if agent._is_plan_tool_call(name, descriptor):
                return await agent._finalize_execute(execute_start, {
                    "success": False,
                    "outputs": outputs,
                    "errors": errors,
                    "encountered_plan_tool": True,
                    "plan_tool_name": name,
                })

            tool_name = name or capability_id
            args = tool_call.get("arguments", {})
            if "path" in args:
                agent._log(f"🔧 Calling [{tool_name}] path={args.get('path')}")
            elif "command" in args:
                agent._log(f"🔧 Calling [{tool_name}] command={args.get('command', '')[:50]}")
            elif "query" in args:
                agent._log(f"🔧 Calling [{tool_name}] query={args.get('query', '')[:50]}")
            else:
                agent._log(f"🔧 Calling [{tool_name}] params={list(args.keys())}")

            tool_result = await agent._run_tool_loop(
                ToolLoopRequest(
                    capability_id=capability_id,
                    params=tool_call.get("arguments", {}),
                ),
                transport=transport,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                descriptor=descriptor,
            )

            result_success = tool_result.get("success", False)
            result_output = tool_result.get("output", {})
            result_error = tool_result.get("error", "")
            result_status = tool_result.get("status", "success" if result_success else "fail")

            if result_success and agent._is_skill_tool_call(descriptor):
                agent._mount_skill_from_result(result_output)

            if result_success:
                agent._log(f"   ✅ Success: {result_output}")
            else:
                agent._log(f"   ❌ Failed({result_status}): {result_error}")

            tool_result_content = json.dumps(
                {
                    "success": result_success,
                    "status": result_status,
                    "output": result_output,
                    "error": None if result_success else result_error,
                },
                default=str,
            )
            tool_msg = Message(
                role="tool",
                kind="tool_result",
                name=tool_call_id or capability_id,
                text=tool_result_content,
                data={
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "success": result_success,
                    "status": result_status,
                    "output": result_output,
                    "error": None if result_success else result_error,
                },
            )
            agent._context.stm_add(tool_msg)

            outputs.append(tool_result)

            if not result_success:
                errors.append(result_error or ("tool not allowed" if result_status == "not_allow" else "tool failed"))

        before_context_dispatch = await agent._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
        assembled = agent._context.assemble()
        assembled_messages, assembled_tools, assembled_metadata = agent._apply_context_patch(
            assembled,
            before_context_dispatch,
        )
        await agent._emit_hook(
            HookPhase.AFTER_CONTEXT_ASSEMBLE,
            {
                **agent._context_stats(assembled_messages, len(assembled_tools)),
                "budget_stats": agent._budget_stats(),
            },
        )
        model_input = ModelInput(
            messages=assembled_messages,
            tools=assembled_tools,
            metadata=assembled_metadata,
        )

    errors.append("max tool iterations reached")
    return await agent._finalize_execute(execute_start, {
        "success": False,
        "outputs": outputs,
        "errors": errors,
    })


__all__ = ["run_execute_loop"]
