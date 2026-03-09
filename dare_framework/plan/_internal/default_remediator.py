"""Default LLM-based remediator implementation.

Provides a default IRemediator implementation with a meta-cognitive
reflection prompt. The remediator analyzes failures and generates
structured insights to guide the next planning attempt.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from dare_framework.context import Message
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput
from dare_framework.plan.types import VerifyResult

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.model.kernel import IModelAdapter


# =============================================================================
# Default Reflection System Prompt
# =============================================================================

DEFAULT_REFLECT_SYSTEM_PROMPT = """You are a **Reflection Agent** performing meta-cognitive analysis.

## Your Role

A previous execution attempt has FAILED. Your job is to:
1. **Analyze** what went wrong (root cause analysis)
2. **Reflect** on why the approach didn't work (meta-cognition)
3. **Suggest** adjustments for the next attempt (actionable insights)

## Important Context

You are part of a feedback loop:
- Your analysis will be fed back to the Planner for the next attempt
- The strategic goal (Plan) remains unchanged — we only adjust tactics
- Focus on ACTIONABLE insights, not just descriptions of failure

## Output Format

Provide your reflection as a structured analysis:

```
## Failure Analysis

**What Failed**: [specific error or unexpected behavior]
**Root Cause**: [why this happened]

## Meta-Reflection

**Assumption That Broke**: [what we assumed that turned out wrong]
**Learning**: [what we now understand better]

## Recommended Adjustments

1. [Specific tactical adjustment #1]
2. [Specific tactical adjustment #2]

## Summary for Next Attempt

[One paragraph summarizing what the next planning attempt should do differently]
```

## Principles

1. **Be Specific**: Don't just say "it failed" — explain exactly what failed and why
2. **Be Actionable**: Every insight should lead to a concrete next step
3. **Preserve Goals**: The strategic objective doesn't change, only the approach
4. **Learn Forward**: Focus on what TO DO, not just what NOT to do

## Example

If CI failed due to missing dependency:

```
## Failure Analysis

**What Failed**: CI pipeline failed with DependencyError
**Root Cause**: Production base image missing lib-wushan-pdp package

## Meta-Reflection

**Assumption That Broke**: Assumed local environment matched production
**Learning**: Must verify production dependencies before code changes

## Recommended Adjustments

1. Update Dockerfile to use base image v1.5 which includes the dependency
2. Add pre-commit check for dependency compatibility

## Summary for Next Attempt

Before pushing code changes, verify that all dependencies are available in the
production base image. Update the Dockerfile to use the correct base image
version (v1.5+) that includes lib-wushan-pdp.
```
"""


class DefaultRemediator:
    """Default LLM-based remediator with meta-cognitive reflection prompt.

    This remediator analyzes verification failures and generates
    structured reflection text to guide the next planning attempt.
    """

    def __init__(
        self,
        model: IModelAdapter,
        *,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the default remediator.

        Args:
            model: Model adapter for LLM calls.
            system_prompt: Optional custom system prompt.
            verbose: Whether to print debug output.
        """
        self._model = model
        self._system_prompt = system_prompt or DEFAULT_REFLECT_SYSTEM_PROMPT
        self._verbose = verbose

    @property
    def component_type(self) -> Literal[ComponentType.REMEDIATOR]:
        """Component type for remediator."""
        return ComponentType.REMEDIATOR

    @property
    def name(self) -> str:
        """Component name."""
        return "default-remediator"

    async def remediate(self, verify_result: VerifyResult, ctx: IContext) -> str:
        """Generate reflection text based on verification failure.

        Args:
            verify_result: The failed verification result.
            ctx: Current context.

        Returns:
            Structured reflection text for the next planning attempt.
        """
        # Build failure context
        errors = verify_result.errors or ["Unknown failure"]
        error_text = "\n".join(f"- {e}" for e in errors)

        # Get recent context for analysis
        messages = ctx.stm_get()
        recent_context = ""
        if messages:
            # Get last few messages for context
            recent = messages[-3:] if len(messages) >= 3 else messages
            recent_context = "\n".join(
                (
                    f"[{m.role}]: {m.text[:200]}..."
                    if m.text is not None and len(m.text) > 200
                    else f"[{m.role}]: {m.text or ''}"
                )
                for m in recent
            )

        user_prompt = f"""## Verification Failed

**Errors**:
{error_text}

**Metadata**:
{verify_result.metadata}

**Recent Context**:
{recent_context}

Please analyze this failure and provide your structured reflection."""

        model_input = ModelInput(
            messages=[
                Message(role="system", text=self._system_prompt),
                Message(role="user", text=user_prompt),
            ],
        )

        if self._verbose:
            print(f"[DefaultRemediator] Analyzing failure: {errors[0][:50]}...")

        try:
            response = await self._model.generate(model_input)
            reflection = response.content.strip()

            if self._verbose:
                print(f"[DefaultRemediator] Generated reflection ({len(reflection)} chars)")

            return reflection

        except Exception as e:
            if self._verbose:
                print(f"[DefaultRemediator] Error: {e}, using fallback")
            return self._fallback_reflection(errors)

    def _fallback_reflection(self, errors: list[str]) -> str:
        """Generate a simple fallback reflection."""
        error_text = "\n".join(f"- {e}" for e in errors)
        return f"""## Failure Analysis

**What Failed**: Verification did not pass
**Errors**: 
{error_text}

## Recommended Adjustments

1. Review the specific errors above
2. Check if prerequisites are met
3. Verify environment configuration

## Summary for Next Attempt

The previous attempt failed with the errors listed above. Please review
the error details and adjust the approach accordingly. Consider checking
dependencies, configurations, and prerequisites before retrying.
"""


__all__ = ["DefaultRemediator", "DEFAULT_REFLECT_SYSTEM_PROMPT"]
