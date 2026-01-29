"""Enhanced FiveLayerAgent with system message for tool calling."""
from typing import Any
from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.model import Prompt
from dare_framework.plan.types import ValidatedPlan


class EnhancedFiveLayerAgent(FiveLayerAgent):
    """FiveLayerAgent with system message to guide model to use tools.

    This fixes the issue where models don't call tools because there's
    no system message instructing them to use the available tools.
    """

    EXECUTE_SYSTEM_PROMPT = """You are a helpful coding assistant with access to tools for file operations.

IMPORTANT INSTRUCTIONS:
1. You MUST use the provided tools to complete tasks - DO NOT just describe what you would do
2. When asked to write/create files, use the write_file tool immediately
3. When asked to read/search files, use read_file or search_code tools
4. DO NOT return explanatory text without calling tools first
5. Call tools step by step to accomplish the task

Available tools:
- write_file: Write content to a file (use this to create code files)
- read_file: Read file contents
- search_code: Search for patterns in code

Remember: TAKE ACTION using tools, don't just explain what you would do!"""

    async def _run_execute_loop(self, plan: ValidatedPlan | None) -> dict[str, Any]:
        """Run execute loop with system message for tool calling.

        This overrides the base implementation to add a system message
        that instructs the model to use tools instead of just returning text.
        """
        # Budget check
        self._context.budget_check()

        # Assemble context for execution
        assembled = self._context.assemble()

        # ENHANCEMENT: Add system message at the beginning if not already present
        messages = assembled.messages.copy()

        # Check if first message is already a system message
        if not messages or messages[0].role != "system":
            # Prepend our system message
            system_msg = Message(role="system", content=self.EXECUTE_SYSTEM_PROMPT)
            messages = [system_msg] + messages

        # Create prompt with enhanced messages
        prompt = Prompt(
            messages=messages,
            tools=assembled.tools,
            metadata=assembled.metadata,
        )

        # DEBUG: Print messages being sent
        print(f"\n[DEBUG] Execute Loop - Messages being sent to model:")
        for i, msg in enumerate(messages, 1):
            # Show full content for debugging
            print(f"  {i}. [{msg.role}]")
            print(f"     Content: {msg.content}")
        print(f"[DEBUG] Tools: {len(prompt.tools)} tools")
        if prompt.tools:
            for tool in prompt.tools[:3]:  # Show first 3 tools
                func = tool.get('function', {})
                print(f"  - {func.get('name', 'N/A')}: {func.get('description', 'N/A')[:60]}")
        print()

        outputs: list[Any] = []
        errors: list[str] = []

        for iteration in range(self._max_tool_iterations):
            # Budget check each iteration
            self._context.budget_check()

            # Check execution control
            if self._exec_ctl is not None:
                self._poll_or_raise()

            # Generate model response
            response = await self._model.generate(prompt)

            await self._log_event("model.response", {
                "iteration": iteration + 1,
                "has_tool_calls": bool(response.tool_calls),
            })

            # No tool calls: we're done
            if not response.tool_calls:
                # Add response to STM
                assistant_message = Message(role="assistant", content=response.content)
                self._context.stm_add(assistant_message)

                # Record token usage
                if response.usage:
                    tokens = response.usage.get("total_tokens", 0)
                    if tokens:
                        self._context.budget_use("tokens", tokens)

                outputs.append({"content": response.content})
                return {
                    "success": True,
                    "outputs": outputs,
                    "errors": errors,
                }

            # Process tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                name = tool_call.get("name", "")

                # Check for plan tool
                if name.startswith("plan:"):
                    return {
                        "success": False,
                        "outputs": outputs,
                        "errors": errors,
                        "encountered_plan_tool": True,
                        "plan_tool_name": name,
                    }

                # Map function name to capability_id
                # Model returns function names (e.g., "write_file")
                # But ToolGateway expects capability IDs (e.g., "tool:write_file")
                capability_id = name
                if not capability_id.startswith("tool:"):
                    capability_id = f"tool:{name}"

                # Run tool loop
                from dare_framework.plan.types import ToolLoopRequest
                tool_result = await self._run_tool_loop(
                    ToolLoopRequest(
                        capability_id=capability_id,  # Use mapped capability_id
                        params=tool_call.get("arguments", {}),
                    )
                )
                tool_results.append(tool_result)
                outputs.append(tool_result)

                if not tool_result.get("success", False):
                    errors.append(tool_result.get("error", "tool failed"))

            # Update context with tool results for next iteration
            # Add assistant message with tool calls
            assistant_message = Message(
                role="assistant",
                content=response.content or "",
                # Note: tool_calls would be added here in full implementation
            )
            self._context.stm_add(assistant_message)

            # Add tool results as separate messages
            for tool_result in tool_results:
                result_content = str(tool_result.get("result", tool_result))
                tool_message = Message(role="user", content=f"Tool result: {result_content}")
                self._context.stm_add(tool_message)

            # Re-assemble for next iteration
            assembled = self._context.assemble()
            messages = assembled.messages.copy()

            # Add system message again for next iteration
            if not messages or messages[0].role != "system":
                system_msg = Message(role="system", content=self.EXECUTE_SYSTEM_PROMPT)
                messages = [system_msg] + messages

            prompt = Prompt(
                messages=messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )

        # Max iterations reached
        errors.append("max tool iterations reached")
        return {
            "success": False,
            "outputs": outputs,
            "errors": errors,
        }


    async def _run_tool_loop(self, request):
        """Run tool loop - override to handle None _session_state in ReAct mode."""
        # Budget check
        self._context.budget_check()

        # Check if tool gateway is available
        if self._tool_gateway is None:
            return {
                "success": False,
                "error": "no tool gateway configured",
            }

        await self._log_event("tool.invoke", {
            "capability_id": request.capability_id,
        })

        try:
            result = await self._tool_gateway.invoke(
                request.capability_id,
                request.params,
                envelope=request.envelope,
            )

            await self._log_event("tool.result", {
                "capability_id": request.capability_id,
                "success": True,
                "params": request.params,  # ← Add for evidence extraction
            })

            # Collect evidence (only if _session_state exists)
            if self._session_state is not None:
                milestone_state = self._session_state.current_milestone_state
                if milestone_state and hasattr(result, "evidence"):
                    for evidence in result.evidence:
                        milestone_state.add_evidence(evidence)

            return {
                "success": True,
                "result": result,
            }

        except Exception as e:
            await self._log_event("tool.error", {
                "capability_id": request.capability_id,
                "error": str(e),
            })
            return {
                "success": False,
                "error": str(e),
            }


__all__ = ["EnhancedFiveLayerAgent"]
