from __future__ import annotations

from types import SimpleNamespace

from dare_framework.model.adapters.openai_adapter import OpenAIModelAdapter


def test_extract_usage_normalizes_reasoning_tokens() -> None:
    adapter = OpenAIModelAdapter()
    response = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 11,
                "completion_tokens": 22,
                "total_tokens": 33,
                "completion_tokens_details": {
                    "reasoning_tokens": 9,
                },
            }
        },
        additional_kwargs={},
    )

    usage = adapter._extract_usage(response)

    assert usage == {
        "prompt_tokens": 11,
        "completion_tokens": 22,
        "total_tokens": 33,
        "reasoning_tokens": 9,
    }


def test_extract_thinking_content_from_response_additional_kwargs() -> None:
    adapter = OpenAIModelAdapter()
    response = SimpleNamespace(
        additional_kwargs={
            "reasoning_content": "internal reasoning",
        },
        response_metadata={},
    )

    assert adapter._extract_thinking_content(response) == "internal reasoning"
