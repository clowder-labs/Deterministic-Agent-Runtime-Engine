"""Formatted output for CLI."""
from dare_framework.plan.types import ProposedPlan
from cli_commands import CLISessionState


class CLIDisplay:
    """Formatted output for CLI."""

    @staticmethod
    def show_plan(plan: ProposedPlan, evidence: dict[int, dict] | None = None) -> None:
        """Display plan with optional evidence.

        Args:
            plan: The proposed plan (containing evidence requirements)
            evidence: Optional dict {step_index: {"status": "✓/✗", "content": "..."}}
        """
        print("\n" + "="*60)
        if evidence is None:
            print("PROPOSED EXECUTION PLAN")
        else:
            print("EXECUTION RESULTS - EVIDENCE COLLECTED")
        print("="*60)
        print(f"\nGoal: {plan.plan_description}")
        print(f"\nEvidence Requirements ({len(plan.steps)}):")

        for i, step in enumerate(plan.steps, 1):
            if evidence is not None and i in evidence:
                # Show filled evidence
                status = evidence[i]["status"]
                content = evidence[i]["content"]
                print(f"\n{i}. {status} {step.description}")
                print(f"   Type: {step.capability_id}")
                if step.params:
                    expected = step.params.get("expected_content") or step.params.get("expected_files") or step.params.get("search_target")
                    if expected:
                        print(f"   Expected: {expected}")
                print(f"   Evidence: {content}")
            else:
                # Show empty evidence slot (awaiting approval)
                print(f"\n{i}. [ ] {step.description}")
                print(f"   Type: {step.capability_id}")
                if step.params:
                    expected = step.params.get("expected_content") or step.params.get("expected_files") or step.params.get("search_target")
                    if expected:
                        print(f"   Expected: {expected}")

        print("\n" + "="*60)
        if evidence is None:
            print("Type /approve to execute, /reject to cancel")
        print()

    @staticmethod
    def show_help() -> None:
        """Display help."""
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS")
        print("="*60)
        print("/mode [plan|execute] - Switch execution mode")
        print("/approve             - Execute pending plan (plan mode)")
        print("/reject              - Cancel pending plan (plan mode)")
        print("/status              - Show session status")
        print("/help                - Show this help")
        print("/quit (or /exit)     - Exit CLI")
        print("\nEXECUTION MODES:")
        print("  execute (默认) - Direct ReAct execution")
        print("                   Agent decides tools and executes immediately")
        print("  plan           - Evidence-based planning")
        print("                   Generate plan → Review → /approve → Execute")
        print("                   Evidence filled after execution (✓/✗)")
        print("="*60 + "\n")

    @staticmethod
    def show_status(state: CLISessionState) -> None:
        """Display session status."""
        print("\n" + "="*60)
        print("SESSION STATUS")
        print("="*60)
        print(f"Mode: {state.mode.value}")
        print(f"Status: {state.status.value}")

        if state.pending_plan:
            print(f"Pending Plan: Yes")
            print(f"  Task: {state.pending_task_description}")
            print(f"  Steps: {len(state.pending_plan.steps)}")
        else:
            print(f"Pending Plan: No")

        print("="*60 + "\n")
