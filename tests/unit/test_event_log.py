import pytest

from dare_framework.event_log import LocalEventLog
from dare_framework.models import Event, EventFilter


@pytest.mark.asyncio
async def test_event_log_hash_chain(tmp_path):
    path = tmp_path / "events.jsonl"
    event_log = LocalEventLog(path=str(path))

    await event_log.append(Event(event_type="test.start", payload={"value": 1}))
    await event_log.append(Event(event_type="test.finish", payload={"value": 2}))

    assert await event_log.verify_chain() is True

    events = await event_log.query(EventFilter(event_type="test.start"))
    assert len(events) == 1
    assert events[0].payload["value"] == 1
