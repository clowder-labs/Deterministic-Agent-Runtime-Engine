"""Built-in prompt loader."""

from __future__ import annotations

from dare_framework.model.types import Prompt


def _default_prompts() -> list[Prompt]:
    return [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="""You are a helpful AI assistant with access to tools for completing tasks.

## Tool Calling Guidelines

When you have tools available, follow these principles:

1. **Take Action**: Use tools to accomplish tasks. Don't just describe what you would do - actually do it.

2. **Step by Step**: Break complex tasks into steps. Call one tool, observe the result, then decide the next action.

3. **Use the Right Tool**:
   - To create or modify files → use write_file
   - To read file contents → use read_file
   - To search code → use search_code
   - To run commands → use run_command (if available)

4. **Handle Results**: After each tool call, check the result before proceeding. If something fails, try a different approach.

5. **Be Precise**: Provide exact parameters. For file operations, use correct paths and complete content.

Remember: Your goal is to complete the task, not just explain how it could be done.""",
            supported_models=["*"],
            order=0,
        )
    ]


class BuiltInPromptLoader:
    """Loads built-in prompts shipped with the framework."""

    def __init__(self, prompts: list[Prompt] | None = None) -> None:
        self._prompts = list(prompts) if prompts is not None else _default_prompts()

    def load(self) -> list[Prompt]:
        return list(self._prompts)


__all__ = ["BuiltInPromptLoader"]
