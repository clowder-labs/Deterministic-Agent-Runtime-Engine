from __future__ import annotations

from dare_framework.model.builtin_prompt_loader import BuiltInPromptLoader


def test_base_system_prompt_contains_runtime_environment_section() -> None:
    loader = BuiltInPromptLoader()

    prompts = loader.load()
    base_prompt = next(prompt for prompt in prompts if prompt.prompt_id == "base.system")

    assert "## Runtime Environment" in base_prompt.content
    assert "- Current working directory:" in base_prompt.content
    assert "- System:" in base_prompt.content
    assert "- Shell:" in base_prompt.content
    assert "- python:" in base_prompt.content
    assert "- node:" in base_prompt.content
    assert "- bash:" in base_prompt.content
    assert "- git:" in base_prompt.content
