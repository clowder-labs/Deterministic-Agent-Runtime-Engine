from __future__ import annotations

import pytest

from dare_framework.security.errors import SECURITY_TRUST_DERIVATION_FAILED, SecurityBoundaryError
from dare_framework.security.impl import NoOpSecurityBoundary, PolicySecurityBoundary
from dare_framework.security.types import PolicyDecision, RiskLevel


@pytest.mark.asyncio
async def test_noop_security_boundary_allows_policy() -> None:
    boundary = NoOpSecurityBoundary()
    trusted = await boundary.verify_trust(
        input={"path": "README.md"},
        context={"capability_id": "read_file"},
    )
    decision = await boundary.check_policy(
        action="invoke_tool",
        resource="read_file",
        context={"trusted_input": trusted},
    )

    assert trusted.params == {"path": "README.md"}
    assert decision is PolicyDecision.ALLOW


@pytest.mark.asyncio
async def test_policy_security_boundary_requires_approval_for_high_risk() -> None:
    boundary = PolicySecurityBoundary()
    trusted = await boundary.verify_trust(
        input={"command": "rm -rf /tmp/foo"},
        context={
            "capability_id": "run_command",
            "descriptor": {"metadata": {"risk_level": RiskLevel.NON_IDEMPOTENT_EFFECT.value}},
            "risk_level": RiskLevel.NON_IDEMPOTENT_EFFECT.value,
        },
    )
    decision = await boundary.check_policy(
        action="invoke_tool",
        resource="run_command",
        context={"trusted_input": trusted, "capability_id": "run_command"},
    )

    assert decision is PolicyDecision.APPROVE_REQUIRED


@pytest.mark.asyncio
async def test_policy_security_boundary_denies_blocked_capability() -> None:
    boundary = PolicySecurityBoundary(deny_capability_ids={"run_command"})
    trusted = await boundary.verify_trust(
        input={"command": "ls"},
        context={
            "capability_id": "run_command",
            "risk_level": RiskLevel.READ_ONLY.value,
        },
    )
    decision = await boundary.check_policy(
        action="invoke_tool",
        resource="run_command",
        context={"trusted_input": trusted, "capability_id": "run_command"},
    )

    assert decision is PolicyDecision.DENY


@pytest.mark.asyncio
async def test_policy_security_boundary_strict_trust_requires_metadata() -> None:
    boundary = PolicySecurityBoundary(require_trusted_metadata=True)

    with pytest.raises(SecurityBoundaryError) as exc_info:
        await boundary.verify_trust(
            input={"foo": "bar"},
            context={"capability_id": "tool.echo"},
        )

    assert exc_info.value.code == SECURITY_TRUST_DERIVATION_FAILED
