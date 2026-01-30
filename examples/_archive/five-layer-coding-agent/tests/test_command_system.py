"""Test script to verify command system functionality."""
import asyncio
from cli_commands import parse_command, CLISessionState, ExecutionMode, SessionStatus, CommandType
from cli_display import CLIDisplay
from dare_framework.plan.types import ProposedPlan, ProposedStep


def test_command_parsing():
    """Test command parsing."""
    print("Testing command parsing...")

    # Test slash commands
    from cli_commands import Command
    result = parse_command("/quit")
    assert isinstance(result, Command)
    assert result.type == CommandType.QUIT

    result = parse_command("/help")
    assert isinstance(result, Command)
    assert result.type == CommandType.HELP

    result = parse_command("/mode plan")
    assert isinstance(result, Command)
    assert result.type == CommandType.MODE
    assert result.args == ["plan"]

    # Test task input (non-command)
    result = parse_command("Find all TODO comments")
    assert isinstance(result, tuple)
    assert result[0] is None
    assert result[1] == "Find all TODO comments"

    print("✓ Command parsing tests passed")


def test_session_state():
    """Test session state management."""
    print("\nTesting session state...")

    state = CLISessionState()

    # Check defaults (默认是 Execute mode)
    assert state.mode == ExecutionMode.EXECUTE
    assert state.status == SessionStatus.IDLE
    assert state.pending_plan is None
    assert state.pending_task_description is None

    # Simulate plan pending
    state.pending_plan = "fake_plan"
    state.pending_task_description = "Test task"
    state.status = SessionStatus.AWAITING_APPROVAL

    # Reset task
    state.reset_task()
    assert state.status == SessionStatus.IDLE
    assert state.pending_plan is None
    assert state.pending_task_description is None
    assert state.mode == ExecutionMode.EXECUTE  # Mode should persist

    print("✓ Session state tests passed")


def test_display():
    """Test display formatters."""
    print("\nTesting display formatters...")

    display = CLIDisplay()

    # Test 1: Reading task (file_evidence, summary_evidence)
    plan_read = ProposedPlan(
        plan_description="理解项目结构和功能",
        steps=[
            ProposedStep(
                step_id="evidence_1",
                capability_id="file_evidence",  # Evidence type, not tool name
                params={"expected_files": "至少 2 个源文件", "min_count": 2},
                description="证据：已读取并理解源文件"
            ),
            ProposedStep(
                step_id="evidence_2",
                capability_id="summary_evidence",
                params={"required_content": ["项目类型", "主要功能"]},
                description="证据：生成项目总结"
            ),
        ]
    )

    # Test 2: Writing task (code_creation_evidence, functionality_evidence)
    plan_write = ProposedPlan(
        plan_description="创建可玩的贪吃蛇游戏",
        steps=[
            ProposedStep(
                step_id="evidence_1",
                capability_id="code_creation_evidence",
                params={"expected_files": ["snake.py"], "file_type": "Python游戏"},
                description="证据：创建了贪吃蛇游戏文件"
            ),
            ProposedStep(
                step_id="evidence_2",
                capability_id="functionality_evidence",
                params={"test_method": "运行测试", "expected_behavior": "游戏可玩"},
                description="证据：游戏可以运行并可玩"
            ),
        ]
    )

    # Use reading task for main tests
    plan = plan_read

    # Test plan display without evidence (awaiting approval)
    print("\n--- Plan without evidence (awaiting approval) ---")
    display.show_plan(plan)

    # Test plan display with evidence (after execution)
    evidence = {
        1: {"status": "✓", "content": "已读取 2 个文件: sample.py, README.md"},
        2: {"status": "✗", "content": "未生成总结"}
    }
    print("\n--- Plan with evidence (execution results) ---")
    display.show_plan(plan, evidence=evidence)

    # Test writing task display
    print("\n--- Writing Task Plan (code creation) ---")
    display.show_plan(plan_write)

    # Test writing task with evidence
    evidence_write = {
        1: {"status": "✓", "content": "已创建 1 个文件: snake.py"},
        2: {"status": "✓", "content": "代码已创建（功能待用户测试）"}
    }
    print("\n--- Writing Task Results (with evidence) ---")
    display.show_plan(plan_write, evidence=evidence_write)

    # Test help display
    print("\n--- Help display ---")
    display.show_help()

    # Test status display
    state = CLISessionState()
    print("\n--- Status display ---")
    display.show_status(state)

    print("✓ Display tests passed")


async def test_evidence_tracker():
    """Test evidence tracking."""
    print("\nTesting evidence tracker...")

    from evidence_tracker import extract_evidence_from_agent

    # Create mock agent without event log
    class MockAgent:
        _event_log = None

    agent = MockAgent()
    plan = ProposedPlan(
        plan_description="Test",
        steps=[
            ProposedStep(
                step_id="step1",
                capability_id="read_file",
                params={},
                description="Test"
            )
        ]
    )

    # Should return empty dict when no event log
    evidence = await extract_evidence_from_agent(agent, plan)
    assert evidence == {}

    print("✓ Evidence tracker tests passed")


async def main():
    """Run all tests."""
    print("="*60)
    print("Command System Tests")
    print("="*60)

    test_command_parsing()
    test_session_state()
    test_display()
    await test_evidence_tracker()

    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
