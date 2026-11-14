"""Bounded retry, schema validation, DLQ and observability.

The InMemoryBroker is intentionally non-durable. This module does not
claim transactional ACK/DLQ semantics or durable redelivery.
"""

from __future__ import annotations

import asyncio
import inspect
import math
import time

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.topics import Topic
from astroguard_api.streaming.consumer import ConsumerMessageError


class ReliabilityError(RuntimeError):
    """Base reliability exception."""


class PermanentMessageError(ReliabilityError):
    """A message must not be retried."""


class RetryExhaustedError(ReliabilityError):
    """All configured handler attempts failed."""


class DeadLetterDeliveryError(ReliabilityError):
    """The DLQ event could not be published."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.05
    multiplier: float = 2.0
    max_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 10
        ):
            raise ValueError("max_attempts must be between 1 and 10")

        values = (
            self.initial_delay_seconds,
            self.multiplier,
            self.max_delay_seconds,
        )
        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            for v in values
        ):
            raise ValueError("Retry timing values must be finite numbers")

        if self.initial_delay_seconds < 0:
            raise ValueError("initial delay cannot be negative")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max delay must be >= initial delay")

    def delay_for(self, failed_attempt: int) -> float:
        if (
            isinstance(failed_attempt, bool)
            or not isinstance(failed_attempt, int)
            or failed_attempt < 1
        ):
            raise ValueError("failed_attempt must be a positive integer")

        delay = self.initial_delay_seconds * (
            self.multiplier ** (failed_attempt - 1)
        )
        return min(delay, self.max_delay_seconds)


@dataclass(frozen=True)
class SchemaDefinition:
    event_type: str
    supported_versions: frozenset[int]
    validator: Callable[[EventEnvelope], Any] | None = None
    version_validators: dict[int, Callable[[EventEnvelope], Any]] = field(
        default_factory=dict
    )


class EventSchemaRegistry:
    """Explicit event-type/version allowlist with version-specific validators.

    Compatibility is not inferred from version numbers. Register every
    supported version and provide a validator for each version whose
    payload contract needs validation.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, SchemaDefinition] = {}

    def register(
        self,
        event_type: str,
        versions: set[int] | frozenset[int],
        validator: Callable[[EventEnvelope], Any] | None = None,
        *,
        version_validators: dict[int, Callable[[EventEnvelope], Any]] | None = None,
    ) -> None:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be non-empty")
        if not versions:
            raise ValueError("At least one schema version is required")

        normalized = frozenset(versions)
        if any(
            isinstance(v, bool)
            or not isinstance(v, int)
            or not 1 <= v <= 100
            for v in normalized
        ):
            raise ValueError("Schema versions must be integers from 1 to 100")

        if validator is not None and not callable(validator):
            raise ValueError("validator must be callable")

        version_map = dict(version_validators or {})
        for version, fn in version_map.items():
            if version not in normalized:
                raise ValueError(
                    "A version validator was supplied for an unsupported version"
                )
            if not callable(fn):
                raise ValueError("Version validators must be callable")

        self._definitions[event_type] = SchemaDefinition(
            event_type=event_type,
            supported_versions=normalized,
            validator=validator,
            version_validators=version_map,
        )

    def validate(self, event: EventEnvelope) -> None:
        if not isinstance(event, EventEnvelope):
            raise PermanentMessageError("Message is not an EventEnvelope")

        definition = self._definitions.get(event.event_type)
        if definition is None:
            raise PermanentMessageError(
                f"Unregistered event type: {event.event_type}"
            )

        if event.schema_version not in definition.supported_versions:
            raise PermanentMessageError(
                f"Unsupported schema version {event.schema_version} "
                f"for {event.event_type}"
            )

        validator = (
            definition.version_validators.get(event.schema_version)
            or definition.validator
        )
        if validator is None:
            return

        try:
            result = validator(event)
            if inspect.isawaitable(result):
                close = getattr(result, "close", None)
                if callable(close):
                    close()
                raise PermanentMessageError(
                    "Schema validators must be synchronous"
                )
        except PermanentMessageError:
            raise
        except Exception as exc:
            raise PermanentMessageError(
                f"Schema validation failed: {type(exc).__name__}"
            ) from exc


@dataclass
class StreamingMetrics:
    """Thread-safe process-local counters and queue-depth observations."""

    published: int = 0
    processed: int = 0
    processing_failures: int = 0
    retries: int = 0
    dead_lettered: int = 0
    schema_rejections: int = 0
    consume_failures: int = 0
    acknowledgement_failures: int = 0
    dlq_failures: int = 0
    timeouts: int = 0
    processing_duration_total_seconds: float = 0.0
    processing_duration_max_seconds: float = 0.0
    queue_depth_current: int = 0
    queue_depth_max: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    _COUNTERS = frozenset({
        "published",
        "processed",
        "processing_failures",
        "retries",
        "dead_lettered",
        "schema_rejections",
        "consume_failures",
        "acknowledgement_failures",
        "dlq_failures",
        "timeouts",
    })

    def increment(self, name: str, amount: int = 1) -> None:
        if name not in self._COUNTERS:
            raise ValueError(f"Unknown metric: {name}")
        if (
            isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount < 0
        ):
            raise ValueError("Metric increment must be a non-negative integer")
        with self._lock:
            setattr(self, name, getattr(self, name) + amount)

    def observe_duration(self, seconds: float) -> None:
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("Duration must be finite and non-negative")
        with self._lock:
            self.processing_duration_total_seconds += seconds
            self.processing_duration_max_seconds = max(
                self.processing_duration_max_seconds, seconds
            )

    def observe_queue_depth(self, depth: int) -> None:
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
            raise ValueError("Queue depth must be a non-negative integer")
        with self._lock:
            self.queue_depth_current = depth
            self.queue_depth_max = max(self.queue_depth_max, depth)

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            return {
                name: getattr(self, name)
                for name in sorted(self._COUNTERS)
            } | {
                "processing_duration_total_seconds":
                    self.processing_duration_total_seconds,
                "processing_duration_max_seconds":
                    self.processing_duration_max_seconds,
                "queue_depth_current": self.queue_depth_current,
                "queue_depth_max": self.queue_depth_max,
            }


def classify_failure(exc: Exception) -> str:
    if isinstance(
        exc,
        (
            PermanentMessageError,
            ConsumerMessageError,
            ValueError,
            TypeError,
        ),
    ):
        return "permanent"
    return "transient"


@dataclass(frozen=True)
class PipelineResult:
    received: bool
    acknowledged: bool
    event_id: str | None = None
    attempts: int = 0
    dead_lettered: bool = False
    error_class: str | None = None
    error: str | None = None
    handler_result: Any = None
    processing_seconds: float = 0.0


class ReliableStreamingPipeline:
    """Sequential pipeline with bounded retries and explicit ACK boundaries.

    Handler success and broker acknowledgement are separate operations.
    An ACK failure never re-runs a successful handler in this process.

    DLQ publish and source ACK are not atomic. On InMemoryBroker a consumed
    item is removed before processing; failed DLQ delivery cannot guarantee
    redelivery. A durable broker with transactions/visibility timeouts is
    required for durable at-least-once processing.
    """

    def __init__(
        self,
        broker: Any,
        handler: Callable[[EventEnvelope], Any],
        *,
        source_topic: str,
        schema_registry: EventSchemaRegistry,
        retry_policy: RetryPolicy | None = None,
        metrics: StreamingMetrics | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        if broker is None:
            raise ValueError("broker is required")
        if not callable(handler):
            raise ValueError("handler must be callable")
        for method in ("consume", "acknowledge", "publish"):
            if not callable(getattr(broker, method, None)):
                raise ValueError(f"broker must expose {method}()")
        if not isinstance(schema_registry, EventSchemaRegistry):
            raise ValueError("schema_registry is required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        if source_topic == Topic.DEAD_LETTER.value:
            raise ValueError("DLQ cannot be used as a source topic")

        self.broker = broker
        self.handler = handler
        self.source_topic = source_topic
        self.registry = schema_registry
        self.retry_policy = retry_policy or RetryPolicy()
        self.metrics = metrics or StreamingMetrics()
        self.timeout_seconds = float(timeout_seconds)

    async def _invoke(self, method: Callable[..., Any], *args: Any) -> Any:
        result = method(*args)
        if inspect.isawaitable(result):
            return await asyncio.wait_for(
                result, timeout=self.timeout_seconds
            )
        return result

    def _observe_queue(self) -> None:
        queue_size = getattr(self.broker, "queue_size", None)
        if not callable(queue_size):
            return
        try:
            self.metrics.observe_queue_depth(queue_size(self.source_topic))
        except Exception:
            # Metrics must not break message processing.
            return

    async def _acknowledge(self) -> None:
        await self._invoke(self.broker.acknowledge, self.source_topic)

    async def _publish_dlq(
        self,
        event: EventEnvelope,
        *,
        attempts: int,
        error: Exception,
        failure_class: str,
    ) -> None:
        if not isinstance(event, EventEnvelope):
            raise DeadLetterDeliveryError(
                "Cannot construct a DLQ event from an invalid envelope"
            )

        now = datetime.now(timezone.utc)
        dlq_event = EventEnvelope(
            event_type="streaming.dead_letter",
            schema_version=1,
            occurred_at=now,
            source="astroguard.reliability",
            channel=event.channel,
            partition_key=event.partition_key,
            payload={
                "original_event_id": str(event.event_id),
                "original_event_type": event.event_type,
                "original_schema_version": event.schema_version,
                "original_source": event.source,
                "original_payload": event.payload,
                "source_topic": self.source_topic,
                "attempts": attempts,
                "failure_class": failure_class,
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],
                "dead_lettered_at": now.isoformat(),
            },
        )

        try:
            await self._invoke(
                self.broker.publish,
                Topic.DEAD_LETTER.value,
                dlq_event,
            )
        except Exception as exc:
            self.metrics.increment("dlq_failures")
            raise DeadLetterDeliveryError(
                "DLQ publication failed; source ACK was not attempted"
            ) from exc

        self.metrics.increment("dead_lettered")

    async def _finish_dlq(
        self,
        event: EventEnvelope,
        *,
        attempts: int,
        error: Exception,
        failure_class: str,
        started: float,
    ) -> PipelineResult:
        event_id = str(event.event_id)

        try:
            await self._publish_dlq(
                event,
                attempts=attempts,
                error=error,
                failure_class=failure_class,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self.metrics.observe_duration(elapsed)
            return PipelineResult(
                received=True,
                acknowledged=False,
                event_id=event_id,
                attempts=attempts,
                error_class="dlq_delivery",
                error=type(exc).__name__,
                processing_seconds=elapsed,
            )

        try:
            await self._acknowledge()
        except Exception as exc:
            self.metrics.increment("acknowledgement_failures")
            elapsed = time.perf_counter() - started
            self.metrics.observe_duration(elapsed)
            return PipelineResult(
                received=True,
                acknowledged=False,
                event_id=event_id,
                attempts=attempts,
                dead_lettered=True,
                error_class="acknowledgement",
                error=type(exc).__name__,
                processing_seconds=elapsed,
            )

        elapsed = time.perf_counter() - started
        self.metrics.observe_duration(elapsed)
        return PipelineResult(
            received=True,
            acknowledged=True,
            event_id=event_id,
            attempts=attempts,
            dead_lettered=True,
            error_class=failure_class,
            error=type(error).__name__,
            processing_seconds=elapsed,
        )

    async def process_once(self) -> PipelineResult:
        started = time.perf_counter()
        self._observe_queue()

        try:
            event = await self._invoke(
                self.broker.consume, self.source_topic
            )
        except asyncio.TimeoutError:
            self.metrics.increment("timeouts")
            self.metrics.increment("consume_failures")
            return PipelineResult(
                received=False,
                acknowledged=False,
                error_class="timeout",
                error="consume_timeout",
            )
        except Exception as exc:
            self.metrics.increment("consume_failures")
            return PipelineResult(
                received=False,
                acknowledged=False,
                error_class="broker",
                error=type(exc).__name__,
            )

        if event is None:
            return PipelineResult(
                received=False,
                acknowledged=False,
            )

        event_id = str(getattr(event, "event_id", "unknown"))
        self._observe_queue()

        try:
            self.registry.validate(event)
        except Exception as exc:
            self.metrics.increment("schema_rejections")
            self.metrics.increment("processing_failures")
            return await self._finish_dlq(
                event,
                attempts=0,
                error=exc,
                failure_class="permanent",
                started=started,
            )

        last_error: Exception | None = None
        attempts = 0

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            attempts = attempt
            try:
                result = await self._invoke(self.handler, event)
            except asyncio.TimeoutError as exc:
                self.metrics.increment("timeouts")
                self.metrics.increment("processing_failures")
                last_error = exc
                failure_class = "transient"
            except Exception as exc:
                self.metrics.increment("processing_failures")
                last_error = exc
                failure_class = classify_failure(exc)
            else:
                # ACK is deliberately outside the handler try/except.
                # An ACK failure must never cause the handler to run again.
                try:
                    await self._acknowledge()
                except Exception as exc:
                    self.metrics.increment("acknowledgement_failures")
                    elapsed = time.perf_counter() - started
                    self.metrics.observe_duration(elapsed)
                    return PipelineResult(
                        received=True,
                        acknowledged=False,
                        event_id=event_id,
                        attempts=attempt,
                        error_class="acknowledgement",
                        error=type(exc).__name__,
                        handler_result=result,
                        processing_seconds=elapsed,
                    )

                self.metrics.increment("processed")
                elapsed = time.perf_counter() - started
                self.metrics.observe_duration(elapsed)
                return PipelineResult(
                    received=True,
                    acknowledged=True,
                    event_id=event_id,
                    attempts=attempt,
                    handler_result=result,
                    processing_seconds=elapsed,
                )

            if failure_class == "permanent":
                break
            if attempt >= self.retry_policy.max_attempts:
                break

            self.metrics.increment("retries")
            delay = self.retry_policy.delay_for(attempt)
            if delay:
                await asyncio.sleep(delay)

        if last_error is None:
            last_error = RetryExhaustedError("No successful processing attempt")

        return await self._finish_dlq(
            event,
            attempts=attempts,
            error=last_error,
            failure_class=classify_failure(last_error),
            started=started,
        )


__all__ = [
    "ReliabilityError",
    "PermanentMessageError",
    "RetryExhaustedError",
    "DeadLetterDeliveryError",
    "RetryPolicy",
    "SchemaDefinition",
    "EventSchemaRegistry",
    "StreamingMetrics",
    "PipelineResult",
    "classify_failure",
    "ReliableStreamingPipeline",
]