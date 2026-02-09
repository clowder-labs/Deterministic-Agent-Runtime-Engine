from __future__ import annotations

import pytest

from dare_framework.agent.builder import load_mcp_toolkit
from dare_framework.model.factories import create_default_prompt_store


def test_create_default_prompt_store_requires_config() -> None:
    with pytest.raises(ValueError, match="non-null Config"):
        create_default_prompt_store(None)


@pytest.mark.asyncio
async def test_load_mcp_toolkit_requires_config() -> None:
    with pytest.raises(ValueError, match="non-null Config"):
        await load_mcp_toolkit(None)  # type: ignore[arg-type]
