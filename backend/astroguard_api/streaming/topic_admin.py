"""Broker-independent topic administration and provisioning."""

import asyncio
from typing import Protocol

from astroguard_api.streaming.topics import (
    TopicSpec,
    get_all_topic_specs,
    resolve_topic,
)


class TopicAlreadyExistsError(RuntimeError):
    pass


class TopicNotFoundError(LookupError):
    pass


class TopicAdminClosedError(RuntimeError):
    pass


class TopicAdminProtocol(Protocol):
    async def create_topic(
        self,
        spec: TopicSpec,
    ) -> bool:
        ...

    async def describe_topic(
        self,
        topic_name: str,
    ) -> TopicSpec:
        ...

    async def list_topics(self) -> tuple[str, ...]:
        ...

    async def ensure_topics(self) -> tuple[str, ...]:
        ...

    async def close(self) -> None:
        ...


class InMemoryTopicAdmin:
    """
    Development-only topic administration implementation.

    Topic definitions exist only in process memory.
    No broker, filesystem persistence or distributed coordination
    is provided.
    """

    def __init__(self):
        self._topics: dict[str, TopicSpec] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    def _ensure_open(self):
        if self._closed:
            raise TopicAdminClosedError("Topic admin is closed")

    async def create_topic(self, spec: TopicSpec) -> bool:
        self._ensure_open()

        if not isinstance(spec, TopicSpec):
            raise TypeError("spec must be a TopicSpec")

        async with self._lock:
            self._ensure_open()

            if spec.name in self._topics:
                existing = self._topics[spec.name]

                if existing != spec:
                    raise TopicAlreadyExistsError(
                        f"Topic already exists with different configuration: "
                        f"{spec.name}"
                    )

                return False

            self._topics[spec.name] = spec
            return True

    async def describe_topic(self, topic_name: str) -> TopicSpec:
        self._ensure_open()

        async with self._lock:
            self._ensure_open()

            try:
                return self._topics[topic_name]
            except KeyError as exc:
                raise TopicNotFoundError(
                    f"Topic not found: {topic_name}"
                ) from exc

    async def list_topics(self) -> tuple[str, ...]:
        self._ensure_open()

        async with self._lock:
            self._ensure_open()
            return tuple(sorted(self._topics.keys()))

    async def ensure_topics(self) -> tuple[str, ...]:
        """
        Provision all registered topics.

        Repeated calls are idempotent when configurations match.
        """
        self._ensure_open()

        created = []

        for spec in get_all_topic_specs():
            was_created = await self.create_topic(spec)

            if was_created:
                created.append(spec.name)

        return tuple(created)

    async def validate_registered_topics(self) -> dict[str, bool]:
        self._ensure_open()

        results = {}

        for spec in get_all_topic_specs():
            try:
                actual = await self.describe_topic(spec.name)
                results[spec.name] = actual == spec
            except TopicNotFoundError:
                results[spec.name] = False

        return results

    async def close(self) -> None:
        async with self._lock:
            self._closed = True


def validate_topic_name(topic_name: str) -> str:
    """Validate a topic name against the registered application topics."""
    spec = resolve_topic(topic_name)
    return spec.name