"""Interactive CLI for demonstrating the five-layer coding agent.

This provides a conversational interface to show:
- User task input
- Agent planning process
- Tool execution with live feedback
- Milestone verification
- Final results

Usage:
    PYTHONPATH=../.. python interactive_cli.py
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from dare_framework.context import IContext
from dare_framework.plan.types import (
    ProposedPlan,
    ProposedStep,
    Task,
    ValidatedPlan,
    VerifyResult,
    RunResult,
)
from enhanced_agent import EnhancedFiveLayerAgent
from dare_framework.tool import (
    ReadFileTool,
    SearchCodeTool,
    WriteFileTool,
    NativeToolProvider,
    DefaultToolGateway,
)
from dare_framework.infra.component import ComponentType

from validators import SimpleValidator
from cli_commands import (
    parse_command, Command, CommandType,
    CLISessionState, ExecutionMode, SessionStatus
)
from cli_display import CLIDisplay
from evidence_tracker import extract_evidence_from_agent

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")


def print_step(emoji: str, text: str):
    """Print a step with emoji."""
    print(f"{Colors.CYAN}{emoji} {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def print_thinking(text: str):
    """Print agent thinking."""
    print(f"{Colors.YELLOW}💭 Agent: {text}{Colors.ENDC}")


class InteractivePlanner:
    """Planner that generates plans based on user input and displays the process."""

    @property
    def component_type(self):
        return ComponentType.PLANNER

    @property
    def name(self) -> str:
        return "interactive-planner"

    def __init__(self, workspace: Path, task_description: str = ""):
        self.workspace = workspace
        self.task_description = task_description

    async def plan(self, ctx: IContext) -> ProposedPlan:
        """Generate a plan based on the task description."""
        task_desc = self.task_description or "Unknown task"

        print_thinking(f"Analyzing task: {task_desc}")
        await asyncio.sleep(0.5)  # Simulate thinking

        # Parse the task and generate appropriate steps
        steps = []

        # Simple keyword-based planning (in real implementation, this would use LLM)
        task_lower = task_desc.lower()

        if "read" in task_lower or "find" in task_lower or "search" in task_lower:
            print_thinking("Planning to read and search files...")

            if "todo" in task_lower:
                steps.append(ProposedStep(
                    step_id="step1",
                    capability_id="search_code",
                    params={"pattern": "TODO", "file_pattern": "*.py"},
                    description="Search for TODO comments in Python files",
                ))
            elif "function" in task_lower or "def" in task_lower:
                steps.append(ProposedStep(
                    step_id="step1",
                    capability_id="search_code",
                    params={"pattern": r"^def\s+\w+", "file_pattern": "*.py"},
                    description="Search for function definitions",
                ))
            else:
                # Default: read sample.py
                steps.append(ProposedStep(
                    step_id="step1",
                    capability_id="read_file",
                    params={"path": str(self.workspace / "sample.py")},
                    description="Read sample.py",
                ))

        elif "write" in task_lower or "create" in task_lower:
            print_thinking("Planning to write/create files...")
            steps.append(ProposedStep(
                step_id="step1",
                capability_id="write_file",
                params={"path": str(self.workspace / "output.txt"), "content": "# Generated output\n"},
                description="Write output file",
            ))

        else:
            # Default plan
            print_thinking("Using default plan: read and search")
            steps.extend([
                ProposedStep(
                    step_id="step1",
                    capability_id="read_file",
                    params={"path": str(self.workspace / "sample.py")},
                    description="Read sample.py",
                ),
                ProposedStep(
                    step_id="step2",
                    capability_id="search_code",
                    params={"pattern": "TODO", "file_pattern": "*.py"},
                    description="Search for TODO comments",
                ),
            ])

        plan = ProposedPlan(
            plan_description=task_desc,
            steps=steps,
        )

        # Display the generated plan
        print_success("Plan generated!")
        print(f"\n{Colors.BOLD}Plan Steps:{Colors.ENDC}")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step.description}")
            print(f"     Tool: {Colors.CYAN}{step.capability_id}{Colors.ENDC}")
            print(f"     Params: {step.params}")
        print()

        return plan


class VerboseValidator(SimpleValidator):
    """Validator that prints detailed verification process."""

    @property
    def name(self) -> str:
        return "verbose-validator"

    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan:
        """Validate the plan and show the process."""
        print_step("🔍", "Validating plan...")
        await asyncio.sleep(0.3)

        result = await super().validate_plan(plan, ctx)

        if result.success:
            print_success("Plan validation passed")
        else:
            print_error(f"Plan validation failed: {result.errors}")

        return result

    async def verify_milestone(self, result: RunResult, ctx: IContext) -> VerifyResult:
        """Verify milestone and show the process."""
        print_step("✅", "Verifying milestone completion...")
        await asyncio.sleep(0.3)

        print_info(f"Execution success: {result.success}")
        if result.errors:
            print_info(f"Execution errors: {result.errors}")

        verify_result = await super().verify_milestone(result, ctx)

        if verify_result.success:
            print_success("Milestone verified successfully!")
        else:
            print_error(f"Milestone verification failed: {verify_result.errors}")

        return verify_result


async def handle_mode_command(cmd: Command, state: CLISessionState) -> None:
    """Handle /mode command."""
    if not cmd.args:
        print(f"Current mode: {state.mode.value}")
        print("Usage: /mode [plan|execute]")
        return

    mode_str = cmd.args[0].lower()
    if mode_str == "plan":
        state.mode = ExecutionMode.PLAN
        print_success("Switched to PLAN mode")
    elif mode_str == "execute":
        state.mode = ExecutionMode.EXECUTE
        print_success("Switched to EXECUTE mode")
    else:
        print_error(f"Unknown mode: {mode_str}")


def handle_reject_command(state: CLISessionState) -> None:
    """Cancel pending plan."""
    if state.status != SessionStatus.AWAITING_APPROVAL:
        print_info("No plan awaiting approval")
        return

    print_info("Plan rejected")
    state.reset_task()


async def run_plan_mode(task_text: str, state: CLISessionState, agent, planner, display: CLIDisplay) -> None:
    """Run in Plan Mode: generate → display → await approval."""
    print_thinking("Generating plan...")
    state.status = SessionStatus.RUNNING

    # Build minimal context
    from dare_framework.context import Message
    agent._context.stm_add(Message(role="user", content=task_text))

    # Generate plan using planner
    try:
        plan = await planner.plan(agent._context)
    except Exception as e:
        print_error(f"Failed to generate plan: {e}")
        state.reset_task()
        return

    # Store and display
    state.pending_plan = plan
    state.pending_task_description = task_text
    state.status = SessionStatus.AWAITING_APPROVAL

    display.show_plan(plan)


async def handle_approve_command(state: CLISessionState, agent, display: CLIDisplay) -> None:
    """Execute approved plan."""
    if state.status != SessionStatus.AWAITING_APPROVAL:
        print_info("No plan awaiting approval")
        return

    print_thinking("Executing plan...")
    state.status = SessionStatus.RUNNING

    # Create task and run agent
    task = Task(
        description=state.pending_task_description,
        task_id=f"task-{id(state.pending_task_description)}"
    )

    result = await agent.run(task)

    # Extract evidence from event log
    evidence = await extract_evidence_from_agent(agent, state.pending_plan)

    # Display result
    print_header("📊 Execution Result")

    # Display plan with evidence marks
    display.show_plan(state.pending_plan, evidence=evidence)

    if result.success:
        print_success("Task completed successfully!")
    else:
        print_error("Task failed")

    if result.output:
        print(f"\n{Colors.BOLD}Output:{Colors.ENDC}")
        print(result.output)

    if result.errors:
        print(f"\n{Colors.BOLD}Errors:{Colors.ENDC}")
        for error in result.errors:
            print(f"  - {error}")

    print()
    state.reset_task()


async def run_execute_mode(task_text: str, agent) -> None:
    """Run in Execute Mode: direct ReAct."""
    print_thinking("Executing (ReAct mode)...")

    task = Task(description=task_text, task_id=f"task-{id(task_text)}")

    print_header("🚀 Agent Execution")
    print_step("1️⃣", "Session Loop - Starting task execution")
    print_step("2️⃣", "Milestone Loop - Breaking into milestones")
    print_step("3️⃣", "Plan Loop - Generating execution plan")
    print()

    result = await agent.run(task)

    # Display result
    print_header("📊 Execution Result")

    if result.success:
        print_success("Task completed successfully!")
    else:
        print_error("Task failed")

    if result.output:
        print(f"\n{Colors.BOLD}Output:{Colors.ENDC}")
        print(result.output)

    if result.errors:
        print(f"\n{Colors.BOLD}Errors:{Colors.ENDC}")
        for error in result.errors:
            print(f"  - {error}")

    print()


async def run_interactive_cli(use_real_model: bool = False):
    """Run the interactive CLI."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    print_header("🤖 Five-Layer Coding Agent - Interactive Demo")
    print(f"Workspace: {workspace}")
    print(f"Mode: {'OpenRouter (Real LLM)' if use_real_model else 'Deterministic (Mock)'}")
    print()

    if use_real_model:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print_error("OPENROUTER_API_KEY not found in environment")
            print("Please create .env file with your API key")
            return

        from model_adapters import OpenRouterModelAdapter
        model = OpenRouterModelAdapter()
        print_success(f"Using OpenRouter model: {model.model_name}")
    else:
        from unittest.mock import AsyncMock
        model = AsyncMock()
        print_info("Using mock model (deterministic mode)")

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(tool_provider)

    print_success("Tools initialized: ReadFile, SearchCode, WriteFile")
    print()

    # Initialize state and display
    state = CLISessionState()  # Default: Execute mode
    display = CLIDisplay()

    print(f"{Colors.BOLD}🤖 Five-Layer Coding Agent CLI{Colors.ENDC}")
    print(f"Mode: {state.mode.value} (use /mode to switch)")
    print()
    display.show_help()

    # Create appropriate planner based on mode
    if use_real_model:
        from planners.llm_planner import LLMPlanner
        planner = LLMPlanner(model, workspace, verbose=True)
    else:
        # For deterministic mode, we'll create planner per task
        planner = None

    validator = VerboseValidator()

    agent = EnhancedFiveLayerAgent(
        name="interactive-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,  # May be None for deterministic mode
        validator=validator,
    )

    # Interactive loop
    while True:
        try:
            # Show prompt
            prompt_prefix = "[Plan Pending] " if state.pending_plan else ""
            user_input = input(f"{Colors.GREEN}{prompt_prefix}> {Colors.ENDC}").strip()

            if not user_input:
                continue

            # Parse input
            parsed = parse_command(user_input)

            # Handle commands
            if isinstance(parsed, Command):
                cmd = parsed

                if cmd.type == CommandType.QUIT:
                    print_success("Goodbye!")
                    break

                elif cmd.type == CommandType.HELP:
                    display.show_help()

                elif cmd.type == CommandType.STATUS:
                    display.show_status(state)

                elif cmd.type == CommandType.MODE:
                    await handle_mode_command(cmd, state)

                elif cmd.type == CommandType.APPROVE:
                    await handle_approve_command(state, agent, display)

                elif cmd.type == CommandType.REJECT:
                    handle_reject_command(state)

            else:
                # Regular input - execute as task
                _, task_text = parsed

                if state.status != SessionStatus.IDLE:
                    print_error(f"Cannot start new task (status: {state.status.value})")
                    continue

                # Create planner for this task if needed (deterministic mode)
                if not use_real_model:
                    task_planner = InteractivePlanner(workspace, task_text)
                    agent._planner = task_planner
                else:
                    task_planner = planner

                if state.mode == ExecutionMode.PLAN:
                    await run_plan_mode(task_text, state, agent, task_planner, display)
                else:
                    await run_execute_mode(task_text, agent)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Use /quit to exit{Colors.ENDC}")
        except Exception as e:
            print_error(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point."""
    use_real_model = False

    if len(sys.argv) > 1 and sys.argv[1] in ['--real', '--openrouter']:
        use_real_model = True

    await run_interactive_cli(use_real_model)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
