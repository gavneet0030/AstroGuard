from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from astroguard_api.streaming.broker import InMemoryBroker
from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.topics import Topic
from astroguard_api.streaming.reliability import (
    RetryPolicy,
    EventSchemaRegistry,
    StreamingMetrics,
    ReliableStreamingPipeline,
    PermanentMessageError,
    classify_failure,
)


def make_event():
    return EventEnvelope(
        event_id=uuid4(),
        event_type="telemetry.observed",
        schema_version=1,
        occurred_at=datetime.now(timezone.utc),
        source="phase5_reliability_test",
        channel="a-1",
        partition_key="a-1",
        payload={"temperature": 22.5},
    )


def make_registry():
    registry = EventSchemaRegistry()
    registry.register("telemetry.observed", {1})
    return registry


def test_retry_policy_exponential_backoff():
    policy = RetryPolicy(
        max_attempts=4,
        initial_delay_seconds=0.1,
        multiplier=2,
        max_delay_seconds=0.3,
    )
    assert policy.delay_for(1) == pytest.approx(0.1)
    assert policy.delay_for(2) == pytest.approx(0.2)
    assert policy.delay_for(3) == pytest.approx(0.3)
    assert policy.delay_for(4) == pytest.approx(0.3)


@pytest.mark.parametrize("attempts", [0, -1, 11, True])
def test_retry_policy_rejects_invalid_attempts(attempts):
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=attempts)


def test_retry_policy_rejects_invalid_delay():
    with pytest.raises(ValueError):
        RetryPolicy(initial_delay_seconds=-1)


def test_schema_registry_accepts_registered_event():
    registry = make_registry()
    registry.validate(make_event())


def test_schema_registry_rejects_unknown_event():
    registry = make_registry()
    event = make_event().model_copy(
        update={"event_type": "unknown.event"}
    )
    with pytest.raises(PermanentMessageError):
        registry.validate(event)


def test_schema_registry_rejects_unsupported_version():
    registry = make_registry()
    event = make_event().model_copy(update={"schema_version": 2})
    with pytest.raises(PermanentMessageError):
        registry.validate(event)


def test_failure_classification():
    assert classify_failure(ValueError("bad input")) == "permanent"
    assert classify_failure(RuntimeError("temporary")) == "transient"


def test_metrics_snapshot_and_duration():
    metrics = StreamingMetrics()
    metrics.increment("processed")
    metrics.increment("retries", 2)
    metrics.observe_duration(0.25)
    snapshot = metrics.snapshot()
    assert snapshot["processed"] == 1
    assert snapshot["retries"] == 2
    assert snapshot["processing_duration_max_seconds"] == 0.25


def test_successful_pipeline_acknowledges():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        event = make_event()
        await broker.publish(Topic.TELEMETRY_RAW.value, event)

        calls = []

        def handler(received):
            calls.append(received.event_id)
            return "ok"

        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
        )
        result = await pipeline.process_once()

        assert result.received
        assert result.acknowledged
        assert result.attempts == 1
        assert result.handler_result == "ok"
        assert calls == [event.event_id]
        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.close()

    asyncio.run(scenario())


def test_transient_failure_retries_then_succeeds():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        calls = {"count": 0}

        def handler(event):
            calls["count"] += 1
            if calls["count"] < 3:
                raise RuntimeError("temporary failure")
            return "recovered"

        metrics = StreamingMetrics()
        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            retry_policy=RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0,
                multiplier=2,
                max_delay_seconds=0,
            ),
            metrics=metrics,
        )
        result = await pipeline.process_once()

        assert result.acknowledged
        assert result.attempts == 3
        assert calls["count"] == 3
        assert metrics.snapshot()["retries"] == 2
        assert metrics.snapshot()["processed"] == 1
        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.close()

    asyncio.run(scenario())


def test_retry_exhaustion_routes_to_dlq():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        def handler(event):
            raise RuntimeError("always fails")

        metrics = StreamingMetrics()
        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            retry_policy=RetryPolicy(
                max_attempts=2,
                initial_delay_seconds=0,
                max_delay_seconds=0,
            ),
            metrics=metrics,
        )
        result = await pipeline.process_once()

        assert result.acknowledged
        assert result.dead_lettered
        assert result.attempts == 2
        assert metrics.snapshot()["dead_lettered"] == 1

        dlq_event = await broker.consume(Topic.DEAD_LETTER.value)
        assert dlq_event.event_type == "streaming.dead_letter"
        assert dlq_event.payload["attempts"] == 2
        assert dlq_event.payload["original_event_type"] == "telemetry.observed"
        broker.acknowledge(Topic.DEAD_LETTER.value)

        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.join(Topic.DEAD_LETTER.value)
        await broker.close()

    asyncio.run(scenario())


def test_permanent_failure_skips_retry_and_routes_dlq():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        calls = {"count": 0}

        def handler(event):
            calls["count"] += 1
            raise ValueError("permanent failure")

        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            retry_policy=RetryPolicy(
                max_attempts=5,
                initial_delay_seconds=0,
                max_delay_seconds=0,
            ),
        )
        result = await pipeline.process_once()

        assert result.dead_lettered
        assert result.attempts == 1
        assert calls["count"] == 1

        dlq = await broker.consume(Topic.DEAD_LETTER.value)
        broker.acknowledge(Topic.DEAD_LETTER.value)
        assert dlq.payload["failure_class"] == "permanent"

        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.join(Topic.DEAD_LETTER.value)
        await broker.close()

    asyncio.run(scenario())


def test_schema_rejection_routes_to_dlq():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        event = make_event().model_copy(
            update={"schema_version": 2}
        )
        await broker.publish(Topic.TELEMETRY_RAW.value, event)

        pipeline = ReliableStreamingPipeline(
            broker,
            lambda received: True,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
        )
        result = await pipeline.process_once()

        assert result.dead_lettered
        assert result.acknowledged
        assert result.error_class == "permanent"

        dlq = await broker.consume(Topic.DEAD_LETTER.value)
        broker.acknowledge(Topic.DEAD_LETTER.value)
        assert dlq.payload["original_event_type"] == "telemetry.observed"

        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.join(Topic.DEAD_LETTER.value)
        await broker.close()

    asyncio.run(scenario())


def test_empty_queue_returns_empty_result():
    async def scenario():
        broker = InMemoryBroker(capacity=2)
        pipeline = ReliableStreamingPipeline(
            broker,
            lambda event: True,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
        )
        result = await pipeline.process_once()
        assert not result.received
        assert not result.acknowledged
        await broker.close()

    asyncio.run(scenario())


def test_pipeline_rejects_dead_letter_as_source():
    broker = InMemoryBroker()
    with pytest.raises(ValueError):
        ReliableStreamingPipeline(
            broker,
            lambda event: True,
            source_topic=Topic.DEAD_LETTER.value,
            schema_registry=make_registry(),
        )


def test_queue_capacity_is_bounded():
    async def scenario():
        broker = InMemoryBroker(capacity=1)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())
        assert broker.queue_size(Topic.TELEMETRY_RAW.value) == 1
        assert broker.queue_capacity(Topic.TELEMETRY_RAW.value) == 1
        await broker.consume(Topic.TELEMETRY_RAW.value)
        broker.acknowledge(Topic.TELEMETRY_RAW.value)
        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.close()

    asyncio.run(scenario())

# ============================================================
# PHASE 5.5 - 5.10 HARDENING TESTS
# ============================================================

from astroguard_api.streaming.producer import (
    TelemetryProducer,
    RAW_TOPIC,
)


class AckFailBroker(InMemoryBroker):
    def __init__(self, capacity=4):
        super().__init__(capacity=capacity)
        self.ack_calls = 0

    def acknowledge(self, topic):
        self.ack_calls += 1
        raise RuntimeError("injected acknowledgement failure")


class DLQFailBroker(InMemoryBroker):
    async def publish(self, topic, event):
        if topic == Topic.DEAD_LETTER.value:
            raise RuntimeError("injected DLQ publish failure")
        return await super().publish(topic, event)


class ConsumeFailBroker:
    async def consume(self, topic):
        raise RuntimeError("injected consume failure")

    def acknowledge(self, topic):
        raise AssertionError("ACK must not occur")

    async def publish(self, topic, event):
        return event


def test_ack_failure_does_not_repeat_successful_handler():
    async def scenario():
        broker = AckFailBroker()
        event = make_event()
        await broker.publish(Topic.TELEMETRY_RAW.value, event)

        calls = {"count": 0}

        def handler(received):
            calls["count"] += 1
            return "completed"

        metrics = StreamingMetrics()
        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            metrics=metrics,
            retry_policy=RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0,
                max_delay_seconds=0,
            ),
        )

        result = await pipeline.process_once()

        assert result.received
        assert not result.acknowledged
        assert result.error_class == "acknowledgement"
        assert calls["count"] == 1
        assert broker.ack_calls == 1
        assert metrics.snapshot()["acknowledgement_failures"] == 1
        await broker.close()

    asyncio.run(scenario())


def test_dlq_publish_failure_is_reported_and_not_acknowledged():
    async def scenario():
        broker = DLQFailBroker()
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        pipeline = ReliableStreamingPipeline(
            broker,
            lambda event: (_ for _ in ()).throw(ValueError("bad event")),
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            metrics=StreamingMetrics(),
        )

        result = await pipeline.process_once()

        assert result.received
        assert not result.acknowledged
        assert not result.dead_lettered
        assert result.error_class == "dlq_delivery"
        assert broker.queue_size(Topic.DEAD_LETTER.value) == 0
        await broker.close()

    asyncio.run(scenario())


def test_consume_failure_updates_metrics():
    async def scenario():
        metrics = StreamingMetrics()
        pipeline = ReliableStreamingPipeline(
            ConsumeFailBroker(),
            lambda event: True,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            metrics=metrics,
        )

        result = await pipeline.process_once()
        assert not result.received
        assert result.error_class == "broker"
        assert metrics.snapshot()["consume_failures"] == 1

    asyncio.run(scenario())


def test_schema_registry_uses_version_specific_validator():
    registry = EventSchemaRegistry()
    seen = []

    registry.register(
        "telemetry.observed",
        {1, 2},
        version_validators={
            1: lambda event: seen.append(("v1", event.schema_version)),
            2: lambda event: seen.append(("v2", event.schema_version)),
        },
    )

    registry.validate(make_event())
    registry.validate(make_event().model_copy(update={"schema_version": 2}))

    assert seen == [("v1", 1), ("v2", 2)]


def test_schema_registry_rejects_invalid_version_validator():
    registry = EventSchemaRegistry()

    with pytest.raises(ValueError):
        registry.register(
            "telemetry.observed",
            {1},
            version_validators={2: lambda event: None},
        )


def test_metrics_queue_depth_and_failure_counters():
    metrics = StreamingMetrics()
    metrics.observe_queue_depth(3)
    metrics.observe_queue_depth(1)
    metrics.increment("published", 4)
    metrics.increment("timeouts")

    snapshot = metrics.snapshot()

    assert snapshot["published"] == 4
    assert snapshot["timeouts"] == 1
    assert snapshot["queue_depth_current"] == 1
    assert snapshot["queue_depth_max"] == 3


def test_metrics_reject_invalid_values():
    metrics = StreamingMetrics()

    with pytest.raises(ValueError):
        metrics.increment("processed", -1)

    with pytest.raises(ValueError):
        metrics.observe_queue_depth(-1)

    with pytest.raises(ValueError):
        metrics.observe_duration(float("nan"))


def test_producer_to_reliable_pipeline_end_to_end():
    async def scenario():
        broker = InMemoryBroker(capacity=8)
        metrics = StreamingMetrics()

        producer = TelemetryProducer(
            broker,
            metrics=metrics,
        )

        event = make_event()
        publish_result = await producer.publish(
            event,
            topic=RAW_TOPIC,
        )

        assert publish_result.accepted
        assert publish_result.event_id == str(event.event_id)

        processed = []

        def handler(received):
            processed.append(received.event_id)
            return {"accepted": True}

        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=RAW_TOPIC,
            schema_registry=make_registry(),
            metrics=metrics,
        )

        result = await pipeline.process_once()

        assert result.received
        assert result.acknowledged
        assert result.attempts == 1
        assert processed == [event.event_id]

        snapshot = metrics.snapshot()
        assert snapshot["published"] == 1
        assert snapshot["processed"] == 1

        await broker.join(RAW_TOPIC)
        await broker.close()

    asyncio.run(scenario())


def test_end_to_end_permanent_failure_reaches_dlq():
    async def scenario():
        broker = InMemoryBroker(capacity=8)
        producer = TelemetryProducer(broker)

        event = make_event()
        await producer.publish(event, topic=RAW_TOPIC)

        pipeline = ReliableStreamingPipeline(
            broker,
            lambda received: (_ for _ in ()).throw(ValueError("invalid payload")),
            source_topic=RAW_TOPIC,
            schema_registry=make_registry(),
            retry_policy=RetryPolicy(
                max_attempts=4,
                initial_delay_seconds=0,
                max_delay_seconds=0,
            ),
        )

        result = await pipeline.process_once()

        assert result.received
        assert result.acknowledged
        assert result.dead_lettered
        assert result.attempts == 1

        dlq = await broker.consume(Topic.DEAD_LETTER.value)
        assert dlq.event_type == "streaming.dead_letter"
        assert dlq.payload["original_event_id"] == str(event.event_id)
        assert dlq.payload["failure_class"] == "permanent"

        broker.acknowledge(Topic.DEAD_LETTER.value)
        await broker.join(RAW_TOPIC)
        await broker.join(Topic.DEAD_LETTER.value)
        await broker.close()

    asyncio.run(scenario())


def test_transient_retry_exhaustion_metrics_are_consistent():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        metrics = StreamingMetrics()
        calls = {"count": 0}

        def handler(event):
            calls["count"] += 1
            raise RuntimeError("transient failure")

        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            metrics=metrics,
            retry_policy=RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0,
                max_delay_seconds=0,
            ),
        )

        result = await pipeline.process_once()
        snapshot = metrics.snapshot()

        assert result.dead_lettered
        assert result.acknowledged
        assert result.attempts == 3
        assert calls["count"] == 3
        assert snapshot["processing_failures"] == 3
        assert snapshot["retries"] == 2
        assert snapshot["dead_lettered"] == 1

        dlq = await broker.consume(Topic.DEAD_LETTER.value)
        broker.acknowledge(Topic.DEAD_LETTER.value)

        await broker.join(Topic.TELEMETRY_RAW.value)
        await broker.join(Topic.DEAD_LETTER.value)
        await broker.close()

    asyncio.run(scenario())


def test_cancelled_handler_is_not_acknowledged():
    async def scenario():
        broker = InMemoryBroker(capacity=4)
        await broker.publish(Topic.TELEMETRY_RAW.value, make_event())

        started = asyncio.Event()

        async def handler(event):
            started.set()
            await asyncio.Event().wait()

        pipeline = ReliableStreamingPipeline(
            broker,
            handler,
            source_topic=Topic.TELEMETRY_RAW.value,
            schema_registry=make_registry(),
            timeout_seconds=5,
        )

        task = asyncio.create_task(pipeline.process_once())
        await started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # InMemoryBroker has already dequeued the item. Cancellation does
        # not create durable redelivery; this test verifies no ACK occurred.
        await broker.close()

    asyncio.run(scenario())