import asyncio

import pytest

from dare_framework.hook._internal.hook_runner import run_with_policy


@pytest.mark.asyncio
async def test_timeout_maps_to_hook_timeout_error() -> None:
    async def slow() -> dict[str, str]:
        await asyncio.sleep(0.1)
        return {"decision": "allow"}

    result = await run_with_policy(slow, timeout_ms=1, retries=0, idempotent=False)
    assert result.error_code == "HOOK_TIMEOUT"


@pytest.mark.asyncio
async def test_retry_succeeds_for_idempotent_hooks() -> None:
    attempts = 0

    async def flaky() -> dict[str, str]:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RuntimeError("transient")
        return {"decision": "allow"}

    result = await run_with_policy(flaky, timeout_ms=1000, retries=1, idempotent=True)
    assert result.error_code is None
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_non_idempotent_hook_does_not_retry() -> None:
    attempts = 0

    async def always_fail() -> dict[str, str]:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("fail")

    result = await run_with_policy(always_fail, timeout_ms=1000, retries=3, idempotent=False)
    assert attempts == 1
    assert result.error_code == "HOOK_RUNTIME_ERROR"
