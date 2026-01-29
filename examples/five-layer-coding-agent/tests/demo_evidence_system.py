"""Quick demo of the evidence-based planning system."""
import asyncio
from dare_framework.plan.types import ProposedPlan, ProposedStep
from cli_display import CLIDisplay


def demo_evidence_display():
    """Demonstrate evidence-based plan display."""

    display = CLIDisplay()

    print("\n" + "="*70)
    print("EVIDENCE-BASED PLANNING SYSTEM DEMO")
    print("="*70)

    # Create a plan with evidence requirements (not execution steps!)
    plan = ProposedPlan(
        plan_description="理解这个五层循环 Coding Agent 项目",
        steps=[
            ProposedStep(
                step_id="evidence_1",
                capability_id="file_evidence",  # Evidence type, NOT tool name!
                params={
                    "expected_files": "至少 3 个源文件",
                    "min_count": 3
                },
                description="证据：已读取并理解多个源文件"
            ),
            ProposedStep(
                step_id="evidence_2",
                capability_id="search_evidence",
                params={
                    "search_target": "函数定义和类结构",
                    "min_results": 1
                },
                description="证据：搜索到主要代码结构"
            ),
            ProposedStep(
                step_id="evidence_3",
                capability_id="summary_evidence",
                params={
                    "required_content": ["项目类型", "主要组件", "技术栈"]
                },
                description="证据：生成项目概览总结"
            ),
        ]
    )

    # Step 1: Show plan before execution (awaiting approval)
    print("\n" + "🎯 STEP 1: Plan Generated (Awaiting User Approval)")
    print("-" * 70)
    display.show_plan(plan)

    # Step 2: Show plan after execution (with evidence filled)
    print("\n" + "✅ STEP 2: After Execution (Evidence Collected)")
    print("-" * 70)

    # Simulate evidence collected from event log
    evidence = {
        1: {
            "status": "✓",
            "content": "已读取 5 个文件: interactive_cli.py, llm_planner.py, evidence_tracker.py, cli_display.py, cli_commands.py"
        },
        2: {
            "status": "✓",
            "content": "已搜索: ^def\\s+\\w+, ^class\\s+\\w+"
        },
        3: {
            "status": "✗",
            "content": "未生成总结（Execute Loop 未完成此步骤）"
        }
    }

    display.show_plan(plan, evidence=evidence)

    # Step 3: Explain the difference
    print("\n" + "📋 KEY DIFFERENCES")
    print("="*70)
    print("""
❌ OLD WAY (Execution Steps):
   steps = [
       {"capability_id": "read_file", "params": {"path": "..."}},  # Tool call
       {"capability_id": "search_code", "params": {"pattern": "..."}}
   ]
   → Problem: Execute Loop doesn't use these (pure ReAct mode)

✅ NEW WAY (Evidence Requirements):
   steps = [
       {"capability_id": "file_evidence", "params": {"expected": "..."}},  # Evidence type
       {"capability_id": "summary_evidence", "params": {"required": "..."}}
   ]
   → Benefit: Execute Loop fills evidence after completing task

🎯 ALIGNMENT WITH USER JOURNEY:
   - RIGHT PANE (Plan): Acceptance criteria - "What to achieve" ✅
   - LEFT PANE (Execute): Task list - "How to do it" (ReAct) ✅
""")

    print("="*70)
    print("✓ Demo complete! Run 'PYTHONPATH=../.. python interactive_cli.py --openrouter' to try it")
    print("="*70)


if __name__ == "__main__":
    demo_evidence_display()
