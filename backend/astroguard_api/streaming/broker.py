"""Transport-neutral asynchronous broker protocol and local implementation."""

import asyncio
from collections import defaultdict
from typing import Protocol

from astroguard_api.streaming.contracts import EventEnvelope
from astroguard_api.streaming.topics import resolve_topic


class BrokerClosedError(RuntimeError):
    pass


class BrokerProtocol(Protocol):
    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
    ) -> EventEnvelope:
        ...

    async def consume(self, topic: str) -> EventEnvelope:
        ...

    async def close(self) -> None:
        ...


class InMemoryBroker:
    """
    Bounded asynchronous broker for development and deterministic tests.

    This is NOT a durable distributed message broker.
    Messages are lost when the process exits.
    A successful consume removes the item from the local queue.
    """

    def __init__(self, capacity: int = 256):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")

        if capacity > 100000:
            raise ValueError("capacity exceeds safe maximum")

        self.capacity = capacity
        self._queues: dict[str, asyncio.Queue] = defaultdict(
            lambda: asyncio.Queue(maxsize=self.capacity)
        )
        self._closed = False

    def _get_queue(self, topic: str) -> asyncio.Queue:
        spec = resolve_topic(topic)
        return self._queues[spec.name]

    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
    ) -> EventEnvelope:
        if self._closed:
            raise BrokerClosedError("Broker is closed")

        if not isinstance(event, EventEnvelope):
            raise TypeError("event must be an EventEnvelope")

        spec = resolve_topic(topic)

        if (
            spec.expected_event_type is not None
            and event.event_type != spec.expected_event_type
        ):
            raise ValueError(
                f"Topic {spec.name} expects "
                f"{spec.expected_event_type}, received {event.event_type}"
            )

        queue = self._get_queue(spec.name)

        # await put applies backpressure instead of dropping events.
        await queue.put(event)

        return event

    async def consume(self, topic: str) -> EventEnvelope:
        if self._closed:
            raise BrokerClosedError("Broker is closed")

        queue = self._get_queue(topic)
        return await queue.get()

    def acknowledge(self, topic: str) -> None:
        """
        Mark a consumed local message as processed.

        This is an in-memory queue acknowledgement, not a durable broker ACK.
        """
        queue = self._get_queue(topic)
        queue.task_done()

    def queue_size(self, topic: str) -> int:
        return self._get_queue(topic).qsize()

    def queue_capacity(self, topic: str) -> int:
        return self._get_queue(topic).maxsize

    async def join(self, topic: str) -> None:
        await self._get_queue(topic).join()

    async def close(self) -> None:
        self._closed = True