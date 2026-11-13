from __future__ import annotations

import asyncio
import inspect
import math
from dataclasses import dataclass
from typing import Any, Callable

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.producer import (
    RAW_TOPIC,
    VALIDATED_TOPIC,
    ANOMALY_TOPIC,
    DEAD_LETTER_TOPIC,
)

SUPPORTED_TOPICS = frozenset({
    RAW_TOPIC,
    VALIDATED_TOPIC,
    ANOMALY_TOPIC,
    DEAD_LETTER_TOPIC,
})


class ConsumerError(RuntimeError):
    """Base error for telemetry consumer failures."""


class ConsumerConfigurationError(ConsumerError):
    """Invalid consumer configuration or broker interface."""


class ConsumerMessageError(ConsumerError):
    """Invalid broker message or event contract."""


@dataclass(frozen=True)
class ConsumeResult:
    topic: str
    received: bool
    acknowledged: bool
    event_id: str | None = None
    handler_result: Any = None
    error: str | None = None


@dataclass(frozen=True)
class ConsumeBatchResult:
    topic: str
    requested: int
    received: int
    acknowledged: int
    failed: int
    results: tuple[ConsumeResult, ...]


async def _invoke(method: Callable[..., Any], *args: Any) -> Any:
    result = method(*args)
    if inspect.isawaitable(result):
        return await result
    return result


def _validate_event(event: Any) -> EventEnvelope:
    if not isinstance(event, EventEnvelope):
        raise ConsumerMessageError(
            "Broker message must be an EventEnvelope instance."
        )

    if (
        not isinstance(event.schema_version, int)
        or isinstance(event.schema_version, bool)
        or not 1 <= event.schema_version <= 100
    ):
        raise ConsumerMessageError("Invalid schema_version.")

    if event.channel not in (None, "a-1", "p-1"):
        raise ConsumerMessageError("Unsupported telemetry channel.")

    if not isinstance(event.payload, dict):
        raise ConsumerMessageError("Event payload must be an object.")

    timestamp = event.occurred_at
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ConsumerMessageError("Event timestamp must be timezone-aware.")

    return event


class TelemetryConsumer:
    """Bounded sequential consumer with acknowledgement after successful processing."""

    def __init__(
        self,
        broker: Any,
        handler: Callable[[EventEnvelope], Any],
        *,
        topic: str = RAW_TOPIC,
        timeout_seconds: float = 3.0,
        batch_size: int = 16,
    ) -> None:
        if broker is None:
            raise ConsumerConfigurationError("broker is required.")

        if topic not in SUPPORTED_TOPICS:
            raise ConsumerConfigurationError("Topic is not registered.")

        if not callable(handler):
            raise ConsumerConfigurationError("handler must be callable.")

        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ConsumerConfigurationError(
                "timeout_seconds must be finite and greater than zero."
            )

        if (
            not isinstance(batch_size, int)
            or isinstance(batch_size, bool)
            or not 1 <= batch_size <= 256
        ):
            raise ConsumerConfigurationError(
                "batch_size must be between 1 and 256."
            )

        if not callable(getattr(broker, "consume", None)):
            raise ConsumerConfigurationError("Broker must expose consume().")

        if not callable(getattr(broker, "acknowledge", None)):
            raise ConsumerConfigurationError("Broker must expose acknowledge().")

        self._broker = broker
        self._handler = handler
        self.topic = topic
        self.timeout_seconds = float(timeout_seconds)
        self.batch_size = batch_size

    async def consume_once(self) -> ConsumeResult:
        try:
            message = await asyncio.wait_for(
                _invoke(self._broker.consume, self.topic),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ConsumeResult(
                topic=self.topic,
                received=False,
                acknowledged=False,
                error="ConsumerTimeoutError: broker consume timed out.",
            )
        except Exception as exc:
            return ConsumeResult(
                topic=self.topic,
                received=False,
                acknowledged=False,
                error=f"{type(exc).__name__}: broker consume failed.",
            )

        if message is None:
            return ConsumeResult(
                topic=self.topic,
                received=False,
                acknowledged=False,
            )

        event_id = str(getattr(message, "event_id", "unknown"))

        try:
            event = _validate_event(message)

            handler_result = await asyncio.wait_for(
                _invoke(self._handler, event),
                timeout=self.timeout_seconds,
            )

            await asyncio.wait_for(
                _invoke(self._broker.acknowledge, self.topic),
                timeout=self.timeout_seconds,
            )

            return ConsumeResult(
                topic=self.topic,
                received=True,
                acknowledged=True,
                event_id=event_id,
                handler_result=handler_result,
            )

        except asyncio.TimeoutError:
            return ConsumeResult(
                topic=self.topic,
                received=True,
                acknowledged=False,
                event_id=event_id,
                error="ConsumerTimeoutError: processing or acknowledgement timed out.",
            )
        except Exception as exc:
            return ConsumeResult(
                topic=self.topic,
                received=True,
                acknowledged=False,
                event_id=event_id,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def consume_batch(
        self,
        *,
        max_messages: int | None = None,
    ) -> ConsumeBatchResult:
        limit = self.batch_size if max_messages is None else max_messages

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= self.batch_size
        ):
            raise ConsumerConfigurationError(
                f"max_messages must be between 1 and {self.batch_size}."
            )

        results = []

        for _ in range(limit):
            result = await self.consume_once()

            if not result.received:
                break

            results.append(result)

        received = len(results)
        acknowledged = sum(item.acknowledged for item in results)

        return ConsumeBatchResult(
            topic=self.topic,
            requested=limit,
            received=received,
            acknowledged=acknowledged,
            failed=received - acknowledged,
            results=tuple(results),
        )


__all__ = [
    "ConsumerError",
    "ConsumerConfigurationError",
    "ConsumerMessageError",
    "ConsumeResult",
    "ConsumeBatchResult",
    "TelemetryConsumer",
]