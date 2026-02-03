import asyncio

import pytest

from dare_framework.transport import DefaultAgentChannel, TransportEnvelope, new_envelope_id


class DummyClientChannel:
    def __init__(self, receiver):
        self._receiver = receiver
        self.sender = None

    def attach_agent_envelope_sender(self, sender):
        self.sender = sender

    def agent_envelope_receiver(self):
        return self._receiver


def _envelope(payload: str = "ping") -> TransportEnvelope:
    return TransportEnvelope(id=new_envelope_id(), payload=payload)


@pytest.mark.asyncio
async def test_outbox_backpressure_blocks() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client, max_outbox=1, max_inbox=1)

    await channel.send(_envelope("one"))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel.send(_envelope("two")), timeout=0.1)


@pytest.mark.asyncio
async def test_inbox_backpressure_blocks_sender() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client, max_outbox=1, max_inbox=1)

    sender = client.sender
    assert sender is not None
    await sender(_envelope("one"))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sender(_envelope("two")), timeout=0.1)


@pytest.mark.asyncio
async def test_start_stop_idempotent() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client)

    await channel.start()
    first_task = channel._out_pump_task
    await channel.start()
    assert channel._out_pump_task is first_task

    await channel.stop()


@pytest.mark.asyncio
async def test_stop_drops_outbox() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client, max_outbox=10)

    await channel.send(_envelope("one"))
    await channel.send(_envelope("two"))
    await channel.stop()

    assert channel._outbox.empty()


@pytest.mark.asyncio
async def test_interrupt_cancels_running_task() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    async def long_task() -> None:
        await asyncio.sleep(1)

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client)

    task = asyncio.create_task(channel.run_interruptible(long_task()))
    await asyncio.sleep(0)
    channel.interrupt()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_receiver_errors_are_swallowed() -> None:
    event = asyncio.Event()
    calls = {"count": 0}

    async def receiver(msg: TransportEnvelope) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        event.set()

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client)

    await channel.start()
    await channel.send(_envelope("first"))
    await channel.send(_envelope("second"))

    await asyncio.wait_for(event.wait(), timeout=1.0)
    await channel.stop()


@pytest.mark.asyncio
async def test_sender_errors_are_swallowed() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client)

    async def broken_enqueue(_: TransportEnvelope) -> None:
        raise RuntimeError("boom")

    channel._enqueue_inbox = broken_enqueue  # type: ignore[assignment]

    sender = client.sender
    assert sender is not None
    await sender(_envelope("fail"))


@pytest.mark.asyncio
async def test_encoder_applied_on_send() -> None:
    event = asyncio.Event()
    seen: dict[str, str] = {}

    async def receiver(msg: TransportEnvelope) -> None:
        seen["payload"] = str(msg.payload)
        event.set()

    def encoder(msg: TransportEnvelope) -> TransportEnvelope:
        return TransportEnvelope(
            id=msg.id,
            reply_to=msg.reply_to,
            kind=msg.kind,
            type=msg.type,
            payload=f"{msg.payload}-encoded",
            meta=msg.meta,
            stream_id=msg.stream_id,
            seq=msg.seq,
        )

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client, encoder=encoder)

    await channel.start()
    await channel.send(_envelope("ping"))
    await asyncio.wait_for(event.wait(), timeout=1.0)
    await channel.stop()

    assert seen["payload"] == "ping-encoded"


@pytest.mark.asyncio
async def test_decoder_applied_on_poll() -> None:
    async def receiver(msg: TransportEnvelope) -> None:
        return None

    def decoder(msg: TransportEnvelope) -> TransportEnvelope:
        return TransportEnvelope(
            id=msg.id,
            reply_to=msg.reply_to,
            kind=msg.kind,
            type=msg.type,
            payload=f"{msg.payload}-decoded",
            meta=msg.meta,
            stream_id=msg.stream_id,
            seq=msg.seq,
        )

    client = DummyClientChannel(receiver)
    channel = DefaultAgentChannel.build(client, decoder=decoder)

    sender = client.sender
    assert sender is not None
    await sender(_envelope("ping"))

    msg = await asyncio.wait_for(channel.poll(), timeout=0.5)
    assert msg.payload == "ping-decoded"
