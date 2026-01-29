"""Test fallback plan with evidence types."""
import asyncio
from pathlib import Path
from planners.llm_planner import LLMPlanner
from dare_framework.plan.types import ProposedStep


class MockModel:
    """Mock model that returns tool calls (wrong behavior)."""

    async def generate(self, prompt):
        class Response:
            content = """
{
    "plan_description": "创建贪吃蛇游戏",
    "steps": [
        {
            "step_id": "step1",
            "capability_id": "write_file",
            "params": {"path": "snake.py", "content": "import pygame..."},
            "description": "写代码"
        },
        {
            "step_id": "step2",
            "capability_id": "run_python_file",
            "params": {"path": "snake.py"},
            "description": "运行测试"
        }
    ]
}
"""
        return Response()


async def test_fallback_validation():
    """Test that LLM tool calls are rejected and fallback is used."""
    print("="*70)
    print("Testing Fallback Plan Validation")
    print("="*70)

    workspace = Path(__file__).parent / "workspace"
    model = MockModel()
    planner = LLMPlanner(model, workspace, verbose=True)

    # Simulate a context
    class MockContext:
        def stm_add(self, msg):
            pass

        def stm_get(self):
            from dare_framework.context import Message
            return [Message(role="user", content="写一个可以玩的贪吃蛇")]

    print("\n📋 Testing Task: '写一个可以玩的贪吃蛇'")
    print("-"*70)

    plan = await planner.plan(MockContext())

    print("\n🔍 Checking Plan...")
    print("-"*70)

    # Check 1: Plan should NOT contain tool names
    tool_names = ["write_file", "read_file", "search_code", "run_python", "run_python_file"]
    has_tools = any(
        step.capability_id in tool_names
        for step in plan.steps
    )

    if has_tools:
        print("❌ FAIL: Plan still contains tool names!")
        print(f"   Found: {[s.capability_id for s in plan.steps]}")
        return False
    else:
        print("✓ PASS: Plan uses evidence types (not tool names)")

    # Check 2: Plan should contain evidence types
    evidence_types = ["file_evidence", "search_evidence", "summary_evidence",
                      "code_creation_evidence", "functionality_evidence"]
    has_evidence = any(
        step.capability_id in evidence_types
        for step in plan.steps
    )

    if has_evidence:
        print("✓ PASS: Plan contains evidence types")
    else:
        print("❌ FAIL: Plan doesn't contain evidence types")
        print(f"   Found: {[s.capability_id for s in plan.steps]}")
        return False

    # Display plan
    print("\n📋 Generated Plan:")
    print("-"*70)
    print(f"Description: {plan.plan_description}")
    print(f"Steps ({len(plan.steps)}):")
    for i, step in enumerate(plan.steps, 1):
        print(f"  {i}. Type: {step.capability_id}")
        print(f"     Description: {step.description}")
        print(f"     Params: {step.params}")

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_fallback_validation())
    exit(0 if success else 1)
