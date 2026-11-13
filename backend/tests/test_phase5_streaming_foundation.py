"""Phase 5.1 streaming foundation regression tests."""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.config import StreamingConfig
from astroguard_api.streaming.topics import (
    Topic,
    TOPIC_REGISTRY,
    resolve_topic,
)
from astroguard_api.streaming.broker import (
    InMemoryBroker,
    BrokerClosedError,
)


def make_event(event_type="telemetry.observed"):
    return EventEnvelope(
        event_type=event_type,
        source="phase5-test",
        channel="a-1",
        partition_key="A-1-test",
        occurred_at=datetime.now(timezone.utc),
        payload={"sensor": "temperature", "value": 23.5},
    )


def test_event_envelope_generates_unique_ids():
    first = make_event()
    second = make_event()

    assert first.event_id != second.event_id


def test_event_envelope_requires_timezone():
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_type="telemetry.observed",
            source="test",
            occurred_at=datetime(2026, 1, 1),
            payload={},
        )


def test_event_envelope_rejects_invalid_channel():
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_type="telemetry.observed",
            source="test",
            channel="invalid-channel",
            payload={},
        )


def test_event_envelope_rejects_extra_fields():
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_type="telemetry.observed",
            source="test",
            payload={},
            unexpected="not-allowed",
        )


def test_topic_registry_has_all_expected_topics():
    assert len(TOPIC_REGISTRY) == 4
    assert resolve_topic(Topic.TELEMETRY_RAW).name == (
        "astroguard.telemetry.raw"
    )


def test_unknown_topic_is_rejected():
    with pytest.raises(ValueError):
        resolve_topic("unknown.topic")


def test_streaming_configuration_validation():
    config = StreamingConfig(
        enabled=True,
        transport="memory",
        queue_capacity=8,
    )

    assert config.enabled is True
    assert config.queue_capacity == 8

    with pytest.raises(ValueError):
        StreamingConfig(queue_capacity=0)

    with pytest.raises(ValueError):
        StreamingConfig(transport="unknown")


def test_broker_publish_and_consume():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        event = make_event()

        published = await broker.publish(
            Topic.TELEMETRY_RAW,
            event,
        )

        assert published.event_id == event.event_id
        assert broker.queue_size(Topic.TELEMETRY_RAW) == 1

        received = await broker.consume(Topic.TELEMETRY_RAW)

        assert received.event_id == event.event_id

        broker.acknowledge(Topic.TELEMETRY_RAW)
        await broker.join(Topic.TELEMETRY_RAW)

        assert broker.queue_size(Topic.TELEMETRY_RAW) == 0

        await broker.close()

    asyncio.run(scenario())


def test_broker_enforces_topic_event_contract():
    async def scenario():
        broker = InMemoryBroker(capacity=2)

        with pytest.raises(ValueError):
            await broker.publish(
                Topic.TELEMETRY_RAW,
                make_event("anomaly.detected"),
            )

        await broker.close()

    asyncio.run(scenario())


def test_broker_rejects_unknown_topic():
    async def scenario():
        broker = InMemoryBroker()

        with pytest.raises(ValueError):
            await broker.publish("unknown.topic", make_event())

        await broker.close()

    asyncio.run(scenario())


def test_broker_rejects_publish_after_close():
    async def scenario():
        broker = InMemoryBroker()
        await broker.close()

        with pytest.raises(BrokerClosedError):
            await broker.publish(Topic.TELEMETRY_RAW, make_event())

    asyncio.run(scenario())


def test_broker_capacity_is_bounded():
    async def scenario():
        broker = InMemoryBroker(capacity=1)

        await broker.publish(Topic.TELEMETRY_RAW, make_event())

        assert broker.queue_size(Topic.TELEMETRY_RAW) == 1
        assert broker.queue_capacity(Topic.TELEMETRY_RAW) == 1

        received = await broker.consume(Topic.TELEMETRY_RAW)
        assert received.event_type == "telemetry.observed"

        broker.acknowledge(Topic.TELEMETRY_RAW)
        await broker.join(Topic.TELEMETRY_RAW)
        await broker.close()

    asyncio.run(scenario())


def test_broker_rejects_invalid_capacity():
    with pytest.raises(ValueError):
        InMemoryBroker(capacity=0)