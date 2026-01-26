import pytest

import pytest

pytest.skip(
    "Legacy event log implementation is archived; port to canonical dare_framework once "
    "EventLog implementations exist.",
    allow_module_level=True,
)

from dare_framework.execution.impl.event.local_event_log import LocalEventLog


@pytest.mark.asyncio
async def test_event_log_hash_chain(tmp_path):
    path = tmp_path / "events.jsonl"
    event_log = LocalEventLog(path=str(path))

    await event_log.append("test.start", {"value": 1})
    await event_log.append("test.finish", {"value": 2})

    assert await event_log.verify_chain() is True

    events = await event_log.query(filter={"event_type": "test.start"})
    assert len(events) == 1
    assert events[0].payload["value"] == 1
