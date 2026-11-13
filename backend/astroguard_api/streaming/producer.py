from __future__ import annotations

import asyncio
import inspect
import json
import math

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID


RAW_TOPIC = "astroguard.telemetry.raw"
VALIDATED_TOPIC = "astroguard.telemetry.validated"
ANOMALY_TOPIC = "astroguard.anomalies.detected"
DEAD_LETTER_TOPIC = "astroguard.events.dead-letter"

DEFAULT_MAX_MESSAGE_BYTES = 256 * 1024
DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_BATCH_SIZE = 32

SUPPORTED_CHANNELS = frozenset({"a-1", "p-1"})


class ProducerError(RuntimeError):
    """Base exception for telemetry producer failures."""


class ProducerValidationError(ProducerError):
    """Raised when an event or topic is invalid."""


class ProducerDeliveryError(ProducerError):
    """Raised when the broker rejects or fails a publish operation."""


class ProducerTimeoutError(ProducerDeliveryError):
    """Raised when a publish operation exceeds its timeout."""


@dataclass(frozen=True)
class PublishResult:
    event_id: str
    topic: str
    accepted: bool
    message_bytes: int
    partition_key: str
    broker_result: Any = None
    error: str | None = None


@dataclass(frozen=True)
class BatchPublishResult:
    total: int
    accepted: int
    rejected: int
    results: tuple[PublishResult, ...]


def _json_default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProducerValidationError(
                "Datetime values must be timezone-aware."
            )
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _json_safe(value: Any) -> Any:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
            default=_json_default,
        )
        return json.loads(encoded)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProducerValidationError(
            f"Payload is not valid JSON: {exc}"
        ) from exc


def serialize_event(event: Any) -> bytes:
    """Serialize an EventEnvelope to canonical UTF-8 JSON bytes."""
    required = (
        "event_id",
        "event_type",
        "schema_version",
        "occurred_at",
        "source",
        "channel",
        "partition_key",
        "payload",
    )

    missing = [name for name in required if not hasattr(event, name)]
    if missing:
        raise ProducerValidationError(
            "EventEnvelope fields missing: " + ", ".join(missing)
        )

    event_id = str(event.event_id)
    try:
        UUID(event_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProducerValidationError("event_id must be a UUID.") from exc

    if not isinstance(event.event_type, str) or not event.event_type.strip():
        raise ProducerValidationError("event_type must be non-empty.")

    schema_version = event.schema_version
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or not 1 <= schema_version <= 100
    ):
        raise ProducerValidationError(
            "schema_version must be an integer between 1 and 100."
        )

    if not isinstance(event.source, str) or not event.source.strip():
        raise ProducerValidationError("source must be non-empty.")

    occurred_at = event.occurred_at
    if not isinstance(occurred_at, datetime):
        raise ProducerValidationError("occurred_at must be a datetime.")
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise ProducerValidationError("occurred_at must be timezone-aware.")

    channel = event.channel
    if channel is not None and channel not in SUPPORTED_CHANNELS:
        raise ProducerValidationError("Unsupported telemetry channel.")

    partition_key = event.partition_key
    if not isinstance(partition_key, str) or not partition_key.strip():
        raise ProducerValidationError("partition_key must be non-empty.")

    document = {
        "event_id": event_id,
        "event_type": event.event_type,
        "schema_version": schema_version,
        "occurred_at": occurred_at.astimezone(timezone.utc).isoformat(),
        "source": event.source,
        "channel": channel,
        "partition_key": partition_key,
        "payload": _json_safe(event.payload),
    }

    try:
        return json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProducerValidationError(
            f"Event serialization failed: {exc}"
        ) from exc


def deserialize_event(data: bytes | bytearray | str) -> dict[str, Any]:
    """Decode and structurally validate a serialized event."""
    if isinstance(data, (bytes, bytearray)):
        try:
            text = bytes(data).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProducerValidationError("Message must be UTF-8.") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise ProducerValidationError("Message must be bytes or string.")

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProducerValidationError("Invalid JSON message.") from exc

    if not isinstance(document, dict):
        raise ProducerValidationError("Event JSON root must be an object.")

    required = {
        "event_id", "event_type", "schema_version", "occurred_at",
        "source", "channel", "partition_key", "payload",
    }
    if set(document) != required:
        raise ProducerValidationError(
            "Event JSON fields do not match the envelope contract."
        )

    try:
        UUID(document["event_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProducerValidationError("Invalid event UUID.") from exc

    schema_version = document["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or not 1 <= schema_version <= 100
    ):
        raise ProducerValidationError(
            "schema_version must be an integer between 1 and 100."
        )

    if not isinstance(document["event_type"], str) or not document["event_type"].strip():
        raise ProducerValidationError("event_type must be non-empty.")

    if not isinstance(document["source"], str) or not document["source"].strip():
        raise ProducerValidationError("source must be non-empty.")

    if document["channel"] is not None:
        if document["channel"] not in SUPPORTED_CHANNELS:
            raise ProducerValidationError("Unsupported channel.")

    try:
        timestamp = datetime.fromisoformat(
            document["occurred_at"].replace("Z", "+00:00")
        )
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProducerValidationError("Invalid occurred_at timestamp.") from exc

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ProducerValidationError("occurred_at must include timezone.")

    if not isinstance(document["payload"], dict):
        raise ProducerValidationError("payload must be a JSON object.")

    return document


def resolve_topic(event: Any) -> str:
    """Resolve a topic from event_type without changing the envelope."""
    event_type = str(getattr(event, "event_type", "")).strip().lower()

    if event_type in {
        "telemetry.raw",
        "telemetry.raw.received",
        "raw_telemetry",
    }:
        return RAW_TOPIC

    if event_type in {
        "telemetry.validated",
        "telemetry.accepted",
        "validated_telemetry",
    }:
        return VALIDATED_TOPIC

    if event_type in {
        "anomaly.detected",
        "anomalies.detected",
        "anomaly",
    }:
        return ANOMALY_TOPIC

    if event_type in {
        "dead_letter",
        "event.dead-letter",
        "telemetry.dead-letter",
    }:
        return DEAD_LETTER_TOPIC

    raise ProducerValidationError(
        f"No registered topic mapping for event_type={event_type!r}."
    )


class TelemetryProducer:
    """
    Bounded application producer over the Phase 5.1 BrokerProtocol.

    The producer does not persist to the database and does not claim
    distributed or durable delivery.
    """

    def __init__(
        self,
        broker: Any,
        *,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        if broker is None:
            raise ValueError("broker is required.")
        if max_message_bytes < 128:
            raise ValueError("max_message_bytes must be >= 128.")
        if timeout_seconds <= 0 or not math.isfinite(timeout_seconds):
            raise ValueError("timeout_seconds must be finite and > 0.")
        if batch_size < 1 or batch_size > 256:
            raise ValueError("batch_size must be between 1 and 256.")

        publish = getattr(broker, "publish", None)
        if publish is None or not callable(publish):
            raise TypeError("broker must expose publish().")

        self._broker = broker
        self.max_message_bytes = int(max_message_bytes)
        self.timeout_seconds = float(timeout_seconds)
        self.batch_size = int(batch_size)

        signature = inspect.signature(publish)
        parameters = [
            item for item in signature.parameters.values()
            if item.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        self._publish_parameter_count = len(parameters)

        if self._publish_parameter_count not in (1, 2):
            raise TypeError(
                "Unsupported broker.publish signature. "
                "Expected publish(event) or publish(topic, event)."
            )

    async def _call_broker(self, topic: str, event: Any) -> Any:
        publish = self._broker.publish

        try:
            if self._publish_parameter_count == 1:
                operation = publish(event)
            else:
                operation = publish(topic, event)

            if not inspect.isawaitable(operation):
                raise ProducerDeliveryError(
                    "Broker publish must return an awaitable."
                )

            return await asyncio.wait_for(
                operation,
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ProducerTimeoutError(
                f"Broker publish timed out after {self.timeout_seconds}s."
            ) from exc
        except ProducerDeliveryError:
            raise
        except Exception as exc:
            raise ProducerDeliveryError(
                f"Broker publish failed: {type(exc).__name__}: {exc}"
            ) from exc

    async def publish(
        self,
        event: Any,
        *,
        topic: str | None = None,
    ) -> PublishResult:
        selected_topic = topic or resolve_topic(event)

        allowed = {
            RAW_TOPIC,
            VALIDATED_TOPIC,
            ANOMALY_TOPIC,
            DEAD_LETTER_TOPIC,
        }
        if selected_topic not in allowed:
            raise ProducerValidationError("Topic is not registered.")

        encoded = serialize_event(event)
        message_bytes = len(encoded)

        if message_bytes > self.max_message_bytes:
            raise ProducerValidationError(
                f"Message size {message_bytes} exceeds "
                f"limit {self.max_message_bytes} bytes."
            )

        # Validate the serialized representation before publishing.
        document = deserialize_event(encoded)

        result = await self._call_broker(selected_topic, event)

        return PublishResult(
            event_id=document["event_id"],
            topic=selected_topic,
            accepted=True,
            message_bytes=message_bytes,
            partition_key=document["partition_key"],
            broker_result=result,
        )

    async def publish_batch(
        self,
        events: Iterable[Any],
        *,
        topic: str | None = None,
    ) -> BatchPublishResult:
        """
        Sequential bounded publishing.

        The method deliberately avoids gather() and unbounded task creation.
        A failed event is recorded and does not prevent later events from
        being attempted.
        """
        results: list[PublishResult] = []
        accepted = 0
        rejected = 0
        processed = 0

        for event in events:
            if processed >= self.batch_size:
                raise ProducerValidationError(
                    f"Batch exceeds configured maximum of {self.batch_size}."
                )

            processed += 1

            try:
                result = await self.publish(event, topic=topic)
                results.append(result)
                accepted += 1
            except Exception as exc:
                rejected += 1
                event_id = str(getattr(event, "event_id", "unknown"))
                results.append(
                    PublishResult(
                        event_id=event_id,
                        topic=topic or "unresolved",
                        accepted=False,
                        message_bytes=0,
                        partition_key=str(
                            getattr(event, "partition_key", "")
                        ),
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        return BatchPublishResult(
            total=processed,
            accepted=accepted,
            rejected=rejected,
            results=tuple(results),
        )