"""Centralized topic definitions and validated topic configuration."""

from dataclasses import dataclass
from enum import StrEnum


class Topic(StrEnum):
    TELEMETRY_RAW = "astroguard.telemetry.raw"
    TELEMETRY_VALIDATED = "astroguard.telemetry.validated"
    ANOMALY_EVENTS = "astroguard.anomalies.detected"
    DEAD_LETTER = "astroguard.events.dead-letter"


@dataclass(frozen=True)
class TopicSpec:
    name: str
    description: str
    retention_class: str
    expected_event_type: str | None = None

    partitions: int = 1
    replication_factor: int = 1
    retention_ms: int = 86400000
    cleanup_policy: str = "delete"
    max_message_bytes: int = 1048576

    def __post_init__(self):
        if not self.name or len(self.name) > 249:
            raise ValueError("Topic name must contain 1-249 characters")

        if self.partitions < 1 or self.partitions > 128:
            raise ValueError("partitions must be between 1 and 128")

        if self.replication_factor < 1 or self.replication_factor > 5:
            raise ValueError(
                "replication_factor must be between 1 and 5"
            )

        if self.retention_ms < 60000:
            raise ValueError("retention_ms must be at least 60000")

        if self.cleanup_policy not in {"delete", "compact"}:
            raise ValueError("cleanup_policy must be delete or compact")

        if self.max_message_bytes < 1024:
            raise ValueError("max_message_bytes must be at least 1024")

        if self.max_message_bytes > 10485760:
            raise ValueError("max_message_bytes cannot exceed 10 MiB")

        if not self.retention_class:
            raise ValueError("retention_class cannot be empty")


TOPIC_REGISTRY: dict[Topic, TopicSpec] = {
    Topic.TELEMETRY_RAW: TopicSpec(
        name=Topic.TELEMETRY_RAW.value,
        description="Raw telemetry events before normalization.",
        retention_class="short",
        expected_event_type="telemetry.observed",
        partitions=2,
        replication_factor=1,
        retention_ms=86400000,
        cleanup_policy="delete",
        max_message_bytes=1048576,
    ),
    Topic.TELEMETRY_VALIDATED: TopicSpec(
        name=Topic.TELEMETRY_VALIDATED.value,
        description="Validated and normalized telemetry events.",
        retention_class="standard",
        expected_event_type="telemetry.validated",
        partitions=2,
        replication_factor=1,
        retention_ms=604800000,
        cleanup_policy="delete",
        max_message_bytes=1048576,
    ),
    Topic.ANOMALY_EVENTS: TopicSpec(
        name=Topic.ANOMALY_EVENTS.value,
        description="Anomaly detection output events.",
        retention_class="standard",
        expected_event_type="anomaly.detected",
        partitions=1,
        replication_factor=1,
        retention_ms=604800000,
        cleanup_policy="delete",
        max_message_bytes=1048576,
    ),
    Topic.DEAD_LETTER: TopicSpec(
        name=Topic.DEAD_LETTER.value,
        description="Events rejected after processing failure.",
        retention_class="diagnostic",
        expected_event_type=None,
        partitions=1,
        replication_factor=1,
        retention_ms=2592000000,
        cleanup_policy="delete",
        max_message_bytes=1048576,
    ),
}


def resolve_topic(topic: str | Topic) -> TopicSpec:
    value = topic.value if isinstance(topic, Topic) else topic

    for spec in TOPIC_REGISTRY.values():
        if spec.name == value:
            return spec

    raise ValueError(f"Unknown AstroGuard topic: {value}")


def get_all_topic_specs() -> tuple[TopicSpec, ...]:
    return tuple(TOPIC_REGISTRY.values())