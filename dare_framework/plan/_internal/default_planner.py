"""Default LLM-based planner implementation.

Provides a default IPlanner implementation with a carefully designed
system prompt for evidence-based planning. The planner generates
ProposedPlan with evidence requirements, NOT execution steps.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from dare_framework.context import Message
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput
from dare_framework.plan.types import (
    DecompositionResult,
    Milestone,
    ProposedPlan,
    ProposedStep,
    Task,
)

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.model.kernel import IModelAdapter


# =============================================================================
# Default Planning System Prompt
# =============================================================================

DEFAULT_PLAN_SYSTEM_PROMPT = """You are a **Planning Agent** in an AI-powered development system.

## Your Role

You are NOT an execution agent. You do NOT write code or call tools directly.

Your job is to create an **Implementation Plan** — a strategic contract that defines:
1. **WHAT** needs to be achieved (goals)
2. **WHAT EVIDENCE** is needed to prove completion (acceptance criteria)

Think of yourself as defining a "verification checklist" — what proof do we need to show the task is done?

## Output Structure

You MUST output ONLY valid JSON with this structure:

```json
{
    "plan_description": "Brief description of the goal",
    "steps": [
        {
            "step_id": "evidence_1",
            "capability_id": "EVIDENCE_TYPE",
            "params": {"key": "value"},
            "description": "What evidence is needed"
        }
    ]
}
```

## Evidence Types (capability_id)

Use these evidence types based on the task:

### For Reading/Understanding Tasks:
- `file_evidence` — Proof that files were read and understood
  - params: `{"expected_files": "description", "min_count": N}`
- `search_evidence` — Proof that code/content was searched
  - params: `{"search_target": "what to find", "min_results": N}`
- `summary_evidence` — Proof that analysis was generated
  - params: `{"required_content": ["topic1", "topic2"]}`

### For Writing/Creating Tasks:
- `code_creation_evidence` — Proof that code files were created
  - params: `{"expected_files": ["file1.py"], "file_type": "Python"}`
- `functionality_evidence` — Proof that code works
  - params: `{"test_method": "run/test", "expected_behavior": "description"}`
- `integration_evidence` — Proof of system integration
  - params: `{"target_system": "CI/CD", "expected_status": "pass"}`

## Examples

### Example 1: "What is this project?"
```json
{
    "plan_description": "Understand the project structure and purpose",
    "steps": [
        {
            "step_id": "evidence_1",
            "capability_id": "file_evidence",
            "params": {"expected_files": "README or main source files", "min_count": 2},
            "description": "Evidence: Read and understood key project files"
        },
        {
            "step_id": "evidence_2",
            "capability_id": "summary_evidence",
            "params": {"required_content": ["project type", "main features", "tech stack"]},
            "description": "Evidence: Generated project overview"
        }
    ]
}
```

### Example 2: "Create a snake game"
```json
{
    "plan_description": "Create a playable snake game",
    "steps": [
        {
            "step_id": "evidence_1",
            "capability_id": "code_creation_evidence",
            "params": {"expected_files": ["snake.py"], "file_type": "Python game"},
            "description": "Evidence: Created snake game file"
        },
        {
            "step_id": "evidence_2",
            "capability_id": "functionality_evidence",
            "params": {"test_method": "run", "expected_behavior": "Game launches and responds to input"},
            "description": "Evidence: Game is playable"
        }
    ]
}
```

## Critical Rules

1. **DO NOT** output tool names (read_file, write_file, etc.) as capability_id
2. **DO NOT** write actual code in the plan
3. **DO** focus on WHAT to achieve, not HOW to do it
4. Keep plans simple: 1-4 evidence requirements usually suffice
5. The Execute Loop will decide HOW to collect this evidence using tools
"""


class DefaultPlanner:
    """Default LLM-based planner with evidence-based planning prompt.

    This planner uses a model to generate plans based on user tasks.
    It focuses on defining evidence requirements rather than execution steps.
    """

    def __init__(
        self,
        model: IModelAdapter,
        *,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the default planner.

        Args:
            model: Model adapter for LLM calls.
            system_prompt: Optional custom system prompt (defaults to DEFAULT_PLAN_SYSTEM_PROMPT).
            verbose: Whether to print debug output.
        """
        self._model = model
        self._system_prompt = system_prompt or DEFAULT_PLAN_SYSTEM_PROMPT
        self._verbose = verbose

    @property
    def component_type(self) -> Literal[ComponentType.PLANNER]:
        """Component type for planner."""
        return ComponentType.PLANNER

    @property
    def name(self) -> str:
        """Component name."""
        return "default-planner"

    async def plan(self, ctx: IContext) -> ProposedPlan:
        """Generate a plan using LLM.

        Args:
            ctx: Context containing task information in STM.

        Returns:
            Generated ProposedPlan with evidence requirements.
        """
        # Get task from context STM
        messages = ctx.stm_get()
        task_description = self._describe_task_message(messages[-1] if messages else None)

        # Build prompt
        user_prompt = f"""Task: {task_description}

Please analyze this task and generate an Implementation Plan.
Output ONLY valid JSON following the structure defined in your instructions."""

        model_input = ModelInput(
            messages=[
                Message(role="system", text=self._system_prompt),
                Message(role="user", text=user_prompt),
            ],
        )

        if self._verbose:
            print(f"[DefaultPlanner] Planning for: {task_description[:50]}...")

        # Generate plan
        try:
            response = await self._model.generate(model_input)
            plan_data = self._parse_response(response.content)

            steps = [
                ProposedStep(
                    step_id=step.get("step_id", f"step_{i}"),
                    capability_id=step.get("capability_id", "unknown"),
                    params=step.get("params", {}),
                    description=step.get("description", ""),
                )
                for i, step in enumerate(plan_data.get("steps", []))
            ]

            if self._verbose:
                print(f"[DefaultPlanner] Generated plan with {len(steps)} evidence requirements:")
                print(f"  📋 Plan: {plan_data.get('plan_description', 'N/A')}")
                for i, step in enumerate(steps):
                    print(f"  {i+1}. [{step.capability_id}] {step.description}")
                    if step.params:
                        for k, v in step.params.items():
                            print(f"     - {k}: {v}")

            return ProposedPlan(
                plan_description=plan_data.get("plan_description", task_description),
                steps=steps,
            )

        except Exception as e:
            if self._verbose:
                print(f"[DefaultPlanner] Error: {e}, using fallback")
            return self._fallback_plan(task_description)

    @staticmethod
    def _describe_task_message(message: Message | None) -> str:
        """Build a stable planner task description for text or attachment-only prompts."""
        if message is None:
            return "Unknown task"
        if isinstance(message.text, str):
            normalized_text = message.text.strip()
            if normalized_text:
                return normalized_text
        attachment_count = len(message.attachments or [])
        if attachment_count > 0:
            return f"[User provided {attachment_count} attachment(s) with no text input]"
        return "Unknown task"

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response to extract plan JSON."""
        import json

        content = content.strip()

        # Remove markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        return json.loads(content)

    def _fallback_plan(self, task: str) -> ProposedPlan:
        """Create a simple fallback plan."""
        task_lower = task.lower()

        # Determine task type
        if any(w in task_lower for w in ["写", "创建", "实现", "create", "build", "implement"]):
            return ProposedPlan(
                plan_description=f"Create: {task}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="code_creation_evidence",
                        params={"expected_files": "code files"},
                        description="Evidence: Code files created",
                    ),
                    ProposedStep(
                        step_id="evidence_2",
                        capability_id="functionality_evidence",
                        params={"test_method": "run", "expected_behavior": "works as expected"},
                        description="Evidence: Code works correctly",
                    ),
                ],
            )
        else:
            return ProposedPlan(
                plan_description=f"Understand: {task}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="file_evidence",
                        params={"expected_files": "relevant files", "min_count": 1},
                        description="Evidence: Read relevant files",
                    ),
                    ProposedStep(
                        step_id="evidence_2",
                        capability_id="summary_evidence",
                        params={"required_content": ["answer to the question"]},
                        description="Evidence: Generated response",
                    ),
                ],
            )

    async def decompose(self, task: Task, ctx: IContext) -> DecompositionResult:
        """Decompose a task into milestones.

        Default implementation returns a single milestone from task description.
        Override this method to enable LLM-driven task decomposition.

        Args:
            task: The task to decompose.
            ctx: Current context.

        Returns:
            DecompositionResult with milestones and reasoning.
        """
        from uuid import uuid4

        return DecompositionResult(
            milestones=[
                Milestone(
                    milestone_id=f"{task.task_id or uuid4().hex[:8]}_m1",
                    description=task.description,
                    user_input=(
                        task.input_message.text
                        if task.input_message is not None and task.input_message.text
                        else task.description
                    ),
                )
            ],
            reasoning="Default: single milestone from task description",
        )


__all__ = ["DefaultPlanner", "DEFAULT_PLAN_SYSTEM_PROMPT"]
