"""Unit tests for dare_framework.tool types."""

import time

import pytest

from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    Evidence,
    ExecutionSignal,
    InvocationContext,
    ProviderStatus,
    RiskLevelName,
    ToolResult,
    ToolType,
)


class TestToolType:
    """Tests for ToolType enum."""

    def test_atomic_value(self):
        assert ToolType.ATOMIC.value == "atomic"

    def test_work_unit_value(self):
        assert ToolType.WORK_UNIT.value == "work_unit"


class TestProviderStatus:
    """Tests for ProviderStatus enum."""

    def test_all_statuses_exist(self):
        assert ProviderStatus.HEALTHY.value == "healthy"
        assert ProviderStatus.DEGRADED.value == "degraded"
        assert ProviderStatus.UNHEALTHY.value == "unhealthy"
        assert ProviderStatus.UNKNOWN.value == "unknown"


class TestExecutionSignal:
    """Tests for ExecutionSignal enum."""

    def test_all_signals_exist(self):
        assert ExecutionSignal.NONE.value == "none"
        assert ExecutionSignal.PAUSE_REQUESTED.value == "pause_requested"
        assert ExecutionSignal.CANCEL_REQUESTED.value == "cancel_requested"
        assert ExecutionSignal.HUMAN_APPROVAL_REQUIRED.value == "human_approval_required"


class TestCapabilityType:
    """Tests for CapabilityType enum."""

    def test_all_types_exist(self):
        assert CapabilityType.TOOL.value == "tool"
        assert CapabilityType.AGENT.value == "agent"
        assert CapabilityType.UI.value == "ui"


class TestCapabilityKind:
    """Tests for CapabilityKind enum."""

    def test_all_kinds_exist(self):
        assert CapabilityKind.TOOL.value == "tool"
        assert CapabilityKind.SKILL.value == "skill"
        assert CapabilityKind.PLAN_TOOL.value == "plan_tool"
        assert CapabilityKind.AGENT.value == "agent"
        assert CapabilityKind.UI.value == "ui"


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        result = ToolResult(success=True, output={"data": "test"})
        assert result.success is True
        assert result.output == {"data": "test"}
        assert result.error is None
        assert result.evidence == []

    def test_failure_result(self):
        result = ToolResult(success=False, error="Something failed")
        assert result.success is False
        assert result.error == "Something failed"

    def test_result_is_frozen(self):
        result = ToolResult(success=True)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore


class TestEvidence:
    """Tests for Evidence dataclass."""

    def test_evidence_creation(self):
        evidence = Evidence(
            evidence_id="ev-001",
            kind="file_created",
            payload={"path": "/tmp/test.txt"},
        )
        assert evidence.evidence_id == "ev-001"
        assert evidence.kind == "file_created"
        assert evidence.payload == {"path": "/tmp/test.txt"}
        assert evidence.created_at > 0


class TestInvocationContext:
    """Tests for InvocationContext dataclass."""

    def test_invocation_context_creation(self):
        ctx = InvocationContext(
            invocation_id="inv-001",
            capability_id="echo",
        )
        assert ctx.invocation_id == "inv-001"
        assert ctx.capability_id == "echo"
        assert ctx.parent_id is None
        assert ctx.started_at > 0
        assert ctx.metadata == {}

    def test_invocation_context_with_parent(self):
        ctx = InvocationContext(
            invocation_id="inv-002",
            capability_id="nested",
            parent_id="inv-001",
            metadata={"trace": True},
        )
        assert ctx.parent_id == "inv-001"
        assert ctx.metadata == {"trace": True}


class TestCapabilityDescriptor:
    """Tests for CapabilityDescriptor dataclass."""

    def test_descriptor_creation(self):
        metadata = CapabilityMetadata(
            risk_level="read_only",
            requires_approval=False,
            timeout_seconds=30,
            is_work_unit=False,
            capability_kind=CapabilityKind.TOOL,
        )
        descriptor = CapabilityDescriptor(
            id="test-tool",
            type=CapabilityType.TOOL,
            name="Test Tool",
            description="A test tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            metadata=metadata,
        )
        assert descriptor.id == "test-tool"
        assert descriptor.type == CapabilityType.TOOL
        assert descriptor.name == "Test Tool"
        assert descriptor.metadata is not None
        assert descriptor.metadata["risk_level"] == "read_only"

    def test_descriptor_without_metadata(self):
        descriptor = CapabilityDescriptor(
            id="simple",
            type=CapabilityType.TOOL,
            name="Simple",
            description="Simple tool",
            input_schema={},
        )
        assert descriptor.metadata is None
        assert descriptor.output_schema is None
