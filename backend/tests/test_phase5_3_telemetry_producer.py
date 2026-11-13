from __future__ import annotations

import asyncio
import json

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.producer import (
    TelemetryProducer,
    ProducerValidationError,
    ProducerTimeoutError,
    RAW_TOPIC,
    VALIDATED_TOPIC,
    ANOMALY_TOPIC,
    DEAD_LETTER_TOPIC,
    serialize_event,
    deserialize_event,
    resolve_topic,
)


def make_event(
    event_type="telemetry.raw",
    channel="a-1",
    payload=None,
    partition_key=None,
):
    return EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        occurred_at=datetime.now(timezone.utc),
        source="phase5_3_test",
        channel=channel,
        partition_key=partition_key or channel or "global",
        payload=payload if payload is not None else {"temperature": 21.5},
    )


class FakeBroker:
    def __init__(self):
        self.messages = []
        self.closed = False

    async def publish(self, topic, event):
        if self.closed:
            raise RuntimeError("broker closed")
        self.messages.append((topic, event))
        return {"acknowledged": True, "count": len(self.messages)}


class SlowBroker:
    async def publish(self, topic, event):
        await asyncio.sleep(0.2)
        return True


class RejectBroker:
    async def publish(self, topic, event):
        raise RuntimeError("injected broker failure")


class OneArgumentBroker:
    def __init__(self):
        self.messages = []

    async def publish(self, event):
        self.messages.append(event)
        return True


def test_event_serialization_round_trip():
    event = make_event()
    decoded = deserialize_event(serialize_event(event))
    assert decoded["event_id"] == str(event.event_id)
    assert decoded["schema_version"] == 1
    assert isinstance(decoded["schema_version"], int)
    assert decoded["channel"] == "a-1"
    assert decoded["payload"]["temperature"] == 21.5


def test_event_serialization_is_deterministic():
    event = make_event()
    assert serialize_event(event) == serialize_event(event)


def test_invalid_json_is_rejected():
    with pytest.raises(ProducerValidationError):
        deserialize_event(b"{invalid")


def test_json_root_must_be_object():
    with pytest.raises(ProducerValidationError):
        deserialize_event(b"[]")


def test_unknown_event_fields_are_rejected():
    event = make_event()
    document = json.loads(serialize_event(event))
    document["unexpected"] = True
    with pytest.raises(ProducerValidationError):
        deserialize_event(json.dumps(document))


def test_channel_validation():
    valid_event = make_event()
    event_data = valid_event.model_dump()
    event_data["channel"] = "z-99"
    event = EventEnvelope.model_construct(**event_data)

    with pytest.raises(ProducerValidationError):
        serialize_event(event)


def test_topic_resolution_raw():
    assert resolve_topic(make_event("telemetry.raw")) == RAW_TOPIC


def test_topic_resolution_validated():
    assert resolve_topic(make_event("telemetry.validated")) == VALIDATED_TOPIC


def test_topic_resolution_anomaly():
    assert resolve_topic(make_event("anomaly.detected")) == ANOMALY_TOPIC


def test_topic_resolution_dead_letter():
    assert resolve_topic(make_event("dead_letter")) == DEAD_LETTER_TOPIC


def test_unknown_event_type_rejected():
    with pytest.raises(ProducerValidationError):
        resolve_topic(make_event("unknown.event"))


def test_publish_to_broker():
    broker = FakeBroker()
    producer = TelemetryProducer(broker)
    result = asyncio.run(producer.publish(make_event()))
    assert result.accepted is True
    assert result.topic == RAW_TOPIC
    assert len(broker.messages) == 1


def test_event_id_is_preserved():
    event = make_event()
    broker = FakeBroker()
    result = asyncio.run(TelemetryProducer(broker).publish(event))
    assert result.event_id == str(event.event_id)


def test_explicit_topic_override():
    broker = FakeBroker()
    producer = TelemetryProducer(broker)
    result = asyncio.run(
        producer.publish(make_event(), topic=VALIDATED_TOPIC)
    )
    assert result.topic == VALIDATED_TOPIC


def test_unregistered_topic_rejected():
    producer = TelemetryProducer(FakeBroker())
    with pytest.raises(ProducerValidationError):
        asyncio.run(
            producer.publish(make_event(), topic="not.registered")
        )


def test_message_size_limit():
    producer = TelemetryProducer(
        FakeBroker(),
        max_message_bytes=128,
    )
    event = make_event(payload={"large": "x" * 500})
    with pytest.raises(ProducerValidationError):
        asyncio.run(producer.publish(event))


def test_batch_publishes_sequentially():
    broker = FakeBroker()
    producer = TelemetryProducer(broker, batch_size=4)
    events = [make_event() for _ in range(3)]
    result = asyncio.run(producer.publish_batch(events))
    assert result.total == 3
    assert result.accepted == 3
    assert result.rejected == 0
    assert len(broker.messages) == 3


def test_batch_records_individual_failure():
    producer = TelemetryProducer(RejectBroker(), batch_size=3)
    result = asyncio.run(
        producer.publish_batch([make_event(), make_event()])
    )
    assert result.total == 2
    assert result.accepted == 0
    assert result.rejected == 2


def test_timeout_is_reported():
    producer = TelemetryProducer(
        SlowBroker(),
        timeout_seconds=0.01,
    )
    with pytest.raises(ProducerTimeoutError):
        asyncio.run(producer.publish(make_event()))


def test_one_argument_broker_signature_supported():
    broker = OneArgumentBroker()
    producer = TelemetryProducer(broker)
    result = asyncio.run(producer.publish(make_event()))
    assert result.accepted is True
    assert len(broker.messages) == 1


def test_batch_size_is_bounded():
    producer = TelemetryProducer(FakeBroker(), batch_size=2)
    with pytest.raises(ProducerValidationError):
        asyncio.run(
            producer.publish_batch(
                [make_event(), make_event(), make_event()]
            )
        )


def test_invalid_constructor_limits():
    with pytest.raises(ValueError):
        TelemetryProducer(FakeBroker(), batch_size=0)

    with pytest.raises(ValueError):
        TelemetryProducer(FakeBroker(), timeout_seconds=0)


def test_broker_failure_is_wrapped():
    producer = TelemetryProducer(RejectBroker())
    result = asyncio.run(
        producer.publish_batch([make_event()])
    )
    assert result.rejected == 1
    assert "ProducerDeliveryError" in result.results[0].error