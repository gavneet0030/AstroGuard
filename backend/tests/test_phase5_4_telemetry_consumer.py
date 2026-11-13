from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.consumer import (
    ConsumerConfigurationError,
    TelemetryConsumer,
)
from astroguard_api.streaming.producer import RAW_TOPIC, VALIDATED_TOPIC


def make_event(channel="a-1", event_type="telemetry.raw"):
    return EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        occurred_at=datetime.now(timezone.utc),
        source="phase5_4_test",
        channel=channel,
        partition_key=channel or "global",
        payload={"temperature": 21.5},
    )


class FakeBroker:
    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self.acknowledgements = []
        self.consume_calls = 0

    async def consume(self, topic):
        self.consume_calls += 1
        if not self.messages:
            return None
        return self.messages[0]

    async def acknowledge(self, topic):
        self.acknowledgements.append(topic)
        if self.messages:
            self.messages.pop(0)
        return True


class FailingBroker:
    async def consume(self, topic):
        raise RuntimeError("injected consume failure")

    async def acknowledge(self, topic):
        raise AssertionError("acknowledge must not be called")


def test_consumer_configuration_accepts_registered_topic():
    consumer = TelemetryConsumer(FakeBroker(), lambda event: True)
    assert consumer.topic == RAW_TOPIC


def test_consumer_rejects_unknown_topic():
    with pytest.raises(ConsumerConfigurationError):
        TelemetryConsumer(FakeBroker(), lambda event: True, topic="unknown")


def test_consumer_rejects_invalid_batch_size():
    with pytest.raises(ConsumerConfigurationError):
        TelemetryConsumer(FakeBroker(), lambda event: True, batch_size=0)


def test_consumer_rejects_non_callable_handler():
    with pytest.raises(ConsumerConfigurationError):
        TelemetryConsumer(FakeBroker(), None)


def test_empty_queue_returns_no_message():
    broker = FakeBroker()
    result = asyncio.run(
        TelemetryConsumer(broker, lambda event: True).consume_once()
    )
    assert not result.received
    assert not result.acknowledged
    assert broker.acknowledgements == []


def test_successful_handler_acknowledges_message():
    event = make_event()
    broker = FakeBroker([event])
    processed = []

    def handler(received):
        processed.append(received.event_id)
        return {"processed": True}

    result = asyncio.run(
        TelemetryConsumer(broker, handler).consume_once()
    )

    assert result.received
    assert result.acknowledged
    assert result.event_id == str(event.event_id)
    assert result.handler_result == {"processed": True}
    assert processed == [event.event_id]
    assert broker.acknowledgements == [RAW_TOPIC]
    assert broker.messages == []


def test_handler_failure_does_not_acknowledge():
    event = make_event()
    broker = FakeBroker([event])

    def handler(received):
        raise RuntimeError("injected handler failure")

    result = asyncio.run(
        TelemetryConsumer(broker, handler).consume_once()
    )

    assert result.received
    assert not result.acknowledged
    assert "RuntimeError" in result.error
    assert broker.acknowledgements == []
    assert broker.messages == [event]


def test_async_handler_is_supported():
    event = make_event()
    broker = FakeBroker([event])

    async def handler(received):
        return received.channel

    result = asyncio.run(
        TelemetryConsumer(broker, handler).consume_once()
    )

    assert result.acknowledged
    assert result.handler_result == "a-1"


def test_consumer_batch_is_sequential_and_bounded():
    events = [make_event() for _ in range(3)]
    broker = FakeBroker(events)
    order = []

    def handler(event):
        order.append(event.event_id)
        return True

    result = asyncio.run(
        TelemetryConsumer(
            broker,
            handler,
            batch_size=3,
        ).consume_batch()
    )

    assert result.requested == 3
    assert result.received == 3
    assert result.acknowledged == 3
    assert result.failed == 0
    assert len(order) == 3
    assert broker.messages == []


def test_batch_stops_when_queue_is_empty():
    broker = FakeBroker([make_event()])

    result = asyncio.run(
        TelemetryConsumer(
            broker,
            lambda event: True,
            batch_size=4,
        ).consume_batch()
    )

    assert result.received == 1
    assert result.acknowledged == 1
    assert result.failed == 0


def test_batch_records_failure_and_continues():
    events = [make_event(), make_event()]
    broker = FakeBroker(events)
    calls = []

    def handler(event):
        calls.append(event.event_id)
        if len(calls) == 1:
            raise RuntimeError("first event failure")
        return True

    result = asyncio.run(
        TelemetryConsumer(
            broker,
            handler,
            batch_size=2,
        ).consume_batch()
    )

    assert result.received == 2
    assert result.acknowledged == 1
    assert result.failed == 1
    assert len(calls) == 2
    assert len(broker.messages) == 1


def test_consume_failure_is_reported_without_acknowledgement():
    result = asyncio.run(
        TelemetryConsumer(
            FailingBroker(),
            lambda event: True,
        ).consume_once()
    )

    assert not result.received
    assert not result.acknowledged
    assert "broker consume failed" in result.error


def test_validated_topic_can_be_consumed():
    event = make_event(event_type="telemetry.validated")
    broker = FakeBroker([event])

    result = asyncio.run(
        TelemetryConsumer(
            broker,
            lambda received: received.event_type,
            topic=VALIDATED_TOPIC,
        ).consume_once()
    )

    assert result.topic == VALIDATED_TOPIC
    assert result.acknowledged
    assert result.handler_result == "telemetry.validated"


def test_batch_limit_cannot_exceed_configured_capacity():
    consumer = TelemetryConsumer(
        FakeBroker(),
        lambda event: True,
        batch_size=2,
    )

    with pytest.raises(ConsumerConfigurationError):
        asyncio.run(consumer.consume_batch(max_messages=3))