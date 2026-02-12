"""Tool approval memory end-to-end example.

This example demonstrates the mature approval flow:
1) first approval-required tool call creates a pending request,
2) runtime client grants it with a reusable workspace rule,
3) matching calls auto-pass without asking again,
4) revoking the rule restores pending approval behavior.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder  # noqa: E402
from dare_framework.config import Config  # noqa: E402
from dare_framework.model.kernel import IModelAdapter  # noqa: E402
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse  # noqa: E402
from dare_framework.tool._internal.tools import RunCommandTool  # noqa: E402
from dare_framework.transport import (  # noqa: E402
    AgentChannel,
    DirectClientChannel,
    EnvelopeKind,
    TransportEnvelope,
    new_envelope_id,
)


class ScriptedModelAdapter(IModelAdapter):
    """Deterministic model adapter for reproducible approval demos."""

    def __init__(self, scripted_calls: list[str]) -> None:
        self._scripted_calls = list(scripted_calls)

    @property
    def name(self) -> str:
        return "scripted-approval-demo"

    @property
    def model(self) -> str:
        return "scripted-approval-demo"

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        del options
        if not self._scripted_calls:
            return ModelResponse(content="No scripted calls left.", tool_calls=[])

        command = self._scripted_calls[0]
        if _has_tool_observation_for_current_turn(model_input):
            self._scripted_calls.pop(0)
            return ModelResponse(content=f"Finished command: {command}", tool_calls=[])

        return ModelResponse(
            content=f"Need to run: {command}",
            tool_calls=[
                {
                    "id": f"call_{len(self._scripted_calls)}",
                    "name": "run_command",
                    "arguments": {"command": command},
                }
            ],
        )


def _has_tool_observation_for_current_turn(model_input: ModelInput) -> bool:
    for msg in reversed(model_input.messages):
        role = getattr(msg, "role", "")
        if role == "tool":
            return True
        if role == "user":
            return False
    return False


def _workspace_paths() -> tuple[Path, Path, Path, Path]:
    root = Path(__file__).parent
    workspace = root / "workspace"
    user_dir = workspace / "demo-user-home"
    workspace_rules = workspace / ".dare" / "approvals.json"
    user_rules = user_dir / ".dare" / "approvals.json"
    return workspace, user_dir, workspace_rules, user_rules


def _reset_demo_state(workspace_rules: Path, user_rules: Path) -> None:
    for path in (workspace_rules, user_rules):
        if path.exists():
            path.unlink()


async def _invoke_action(
    client: DirectClientChannel,
    action_id: str,
    **params: Any,
) -> dict[str, Any]:
    response = await client.ask(
        TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.ACTION,
            payload=action_id,
            meta=params,
        ),
        timeout=30.0,
    )
    payload = response.payload
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected action response payload: {payload!r}")
    if payload.get("type") == "error":
        raise RuntimeError(f"action failed ({action_id}): {payload.get('reason')}")

    resp = payload.get("resp")
    if not isinstance(resp, dict):
        raise RuntimeError(f"unexpected action response shape: {payload!r}")

    result = resp.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"unexpected action result shape: {payload!r}")
    return result


async def _wait_for_pending_request_id(
    client: DirectClientChannel,
    *,
    timeout_seconds: float = 5.0,
) -> str:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        listed = await _invoke_action(client, "approvals:list")
        pending = listed.get("pending", [])
        if isinstance(pending, list) and pending:
            first = pending[0]
            if isinstance(first, dict) and isinstance(first.get("request_id"), str):
                return first["request_id"]
        await asyncio.sleep(0.05)
    raise TimeoutError("pending approval request was not created in time")


async def main() -> None:
    workspace, user_dir, workspace_rules, user_rules = _workspace_paths()
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    _reset_demo_state(workspace_rules, user_rules)

    model = ScriptedModelAdapter(
        scripted_calls=[
            "echo first-approval",
            "echo second-auto-pass",
            "echo third-after-revoke",
        ]
    )

    config = Config(
        workspace_dir=str(workspace),
        user_dir=str(user_dir),
    )

    client_channel = DirectClientChannel()
    channel = AgentChannel.build(client_channel)

    agent = await (
        DareAgentBuilder("approval-memory-demo")
        .with_model(model)
        .with_config(config)
        .add_tools(RunCommandTool())
        .with_agent_channel(channel)
        .build()
    )

    await agent.start()
    try:
        print("== 1) first run: pending approval -> grant workspace rule (command_prefix)")
        first_run = asyncio.create_task(agent("Run the first command"))
        first_request_id = await _wait_for_pending_request_id(client_channel)
        print(f"pending request: {first_request_id}")

        granted = await _invoke_action(
            client_channel,
            "approvals:grant",
            request_id=first_request_id,
            scope="workspace",
            matcher="command_prefix",
            matcher_value="echo",
        )
        print(json.dumps(granted, indent=2, ensure_ascii=False))

        first_result = await first_run
        print(f"first run success={first_result.success}, errors={first_result.errors}")

        if workspace_rules.exists():
            print("workspace approvals file:")
            print(workspace_rules.read_text(encoding="utf-8"))

        print("\n== 2) second run: same command prefix auto-pass (no new pending)")
        second_result = await agent("Run the second command")
        listed_after_second = await _invoke_action(client_channel, "approvals:list")
        pending_after_second = listed_after_second.get("pending", [])
        print(f"second run success={second_result.success}, pending_count={len(pending_after_second)}")

        rule = granted.get("rule")
        if not isinstance(rule, dict) or not isinstance(rule.get("rule_id"), str):
            raise RuntimeError("grant response did not include a rule_id")
        rule_id = rule["rule_id"]

        print("\n== 3) revoke workspace rule")
        revoked = await _invoke_action(client_channel, "approvals:revoke", rule_id=rule_id)
        print(json.dumps(revoked, indent=2, ensure_ascii=False))

        print("\n== 4) third run: pending appears again after revoke")
        third_run = asyncio.create_task(agent("Run the third command"))
        third_request_id = await _wait_for_pending_request_id(client_channel)
        print(f"pending request after revoke: {third_request_id}")

        await _invoke_action(
            client_channel,
            "approvals:grant",
            request_id=third_request_id,
            scope="once",
            matcher="exact_params",
        )
        third_result = await third_run
        print(f"third run success={third_result.success}, errors={third_result.errors}")

        final_state = await _invoke_action(client_channel, "approvals:list")
        print("\n== Final approval state")
        print(json.dumps(final_state, indent=2, ensure_ascii=False))
        print(f"workspace rules file: {workspace_rules}")
        print(f"user rules file: {user_rules}")

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
