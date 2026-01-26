"""Unit tests for dare_framework.tool ExecutionControl."""

import asyncio

import pytest

from dare_framework.tool import (
    DefaultExecutionControl,
    Checkpoint,
    ExecutionSignal,
)


class TestDefaultExecutionControl:
    """Tests for DefaultExecutionControl."""

    @pytest.fixture
    def ctrl(self):
        return DefaultExecutionControl()

    def test_initial_signal_is_none(self, ctrl):
        assert ctrl.poll() == ExecutionSignal.NONE

    def test_poll_or_raise_no_signal(self, ctrl):
        # Should not raise
        ctrl.poll_or_raise()

    def test_poll_or_raise_pause_requested(self, ctrl):
        ctrl._signal = ExecutionSignal.PAUSE_REQUESTED
        
        with pytest.raises(InterruptedError) as exc_info:
            ctrl.poll_or_raise()
        
        assert "Pause requested" in str(exc_info.value)

    def test_poll_or_raise_cancel_requested(self, ctrl):
        ctrl._signal = ExecutionSignal.CANCEL_REQUESTED
        
        with pytest.raises(InterruptedError) as exc_info:
            ctrl.poll_or_raise()
        
        assert "Cancel requested" in str(exc_info.value)

    def test_poll_or_raise_human_approval(self, ctrl):
        ctrl._signal = ExecutionSignal.HUMAN_APPROVAL_REQUIRED
        
        with pytest.raises(PermissionError) as exc_info:
            ctrl.poll_or_raise()
        
        assert "Human approval required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pause_creates_checkpoint(self, ctrl):
        checkpoint_id = await ctrl.pause("testing pause")
        
        assert ctrl.poll() == ExecutionSignal.PAUSE_REQUESTED
        assert checkpoint_id is not None
        
        checkpoint = ctrl.get_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.label == "pause"
        assert checkpoint.payload["reason"] == "testing pause"

    @pytest.mark.asyncio
    async def test_resume_clears_signal(self, ctrl):
        checkpoint_id = await ctrl.pause("test")
        assert ctrl.poll() == ExecutionSignal.PAUSE_REQUESTED
        
        await ctrl.resume(checkpoint_id)
        
        assert ctrl.poll() == ExecutionSignal.NONE
        
        checkpoint = ctrl.get_checkpoint(checkpoint_id)
        assert checkpoint.resumed is True

    @pytest.mark.asyncio
    async def test_resume_unknown_checkpoint_raises(self, ctrl):
        with pytest.raises(KeyError) as exc_info:
            await ctrl.resume("unknown-id")
        
        assert "Checkpoint not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, ctrl):
        checkpoint_id = await ctrl.checkpoint("test-label", {"key": "value"})
        
        checkpoint = ctrl.get_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.label == "test-label"
        assert checkpoint.payload == {"key": "value"}
        assert checkpoint.created_at > 0

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, ctrl):
        await ctrl.checkpoint("cp1", {})
        await ctrl.checkpoint("cp2", {})
        
        checkpoints = ctrl.list_checkpoints()
        
        assert len(checkpoints) == 2
        labels = {cp.label for cp in checkpoints}
        assert "cp1" in labels
        assert "cp2" in labels

    @pytest.mark.asyncio
    async def test_wait_for_human_and_resume(self, ctrl):
        checkpoint_id = await ctrl.checkpoint("approval", {"action": "deploy"})
        
        async def resume_after_delay():
            await asyncio.sleep(0.1)
            await ctrl.resume(checkpoint_id)
        
        # Start resume in background
        resume_task = asyncio.create_task(resume_after_delay())
        
        # This should block until resume is called
        await ctrl.wait_for_human(checkpoint_id, "Waiting for approval")
        
        await resume_task
        
        assert ctrl.poll() == ExecutionSignal.NONE
        assert not ctrl.is_pending_approval(checkpoint_id)

    @pytest.mark.asyncio
    async def test_wait_for_human_unknown_checkpoint_raises(self, ctrl):
        with pytest.raises(KeyError):
            await ctrl.wait_for_human("unknown", "reason")

    def test_request_cancel(self, ctrl):
        ctrl.request_cancel()
        assert ctrl.poll() == ExecutionSignal.CANCEL_REQUESTED

    def test_clear_signal(self, ctrl):
        ctrl._signal = ExecutionSignal.PAUSE_REQUESTED
        ctrl.clear_signal()
        assert ctrl.poll() == ExecutionSignal.NONE

    def test_is_pending_approval(self, ctrl):
        assert ctrl.is_pending_approval("any-id") is False
        
        ctrl._pending_approval.add("test-id")
        assert ctrl.is_pending_approval("test-id") is True
