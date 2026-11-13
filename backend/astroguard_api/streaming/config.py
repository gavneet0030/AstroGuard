"""Validated streaming configuration without secret values."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamingConfig:
    enabled: bool = False
    transport: str = "memory"
    queue_capacity: int = 256
    publish_timeout_seconds: float = 5.0
    consumer_batch_size: int = 16

    def __post_init__(self):
        if self.transport not in {"memory", "kafka"}:
            raise ValueError("transport must be memory or kafka")

        if self.queue_capacity < 1 or self.queue_capacity > 100000:
            raise ValueError("queue_capacity must be between 1 and 100000")

        if not 0.05 <= self.publish_timeout_seconds <= 300:
            raise ValueError(
                "publish_timeout_seconds must be between 0.05 and 300"
            )

        if not 1 <= self.consumer_batch_size <= 1000:
            raise ValueError(
                "consumer_batch_size must be between 1 and 1000"
            )

    @classmethod
    def from_environment(cls) -> "StreamingConfig":
        enabled_value = os.getenv(
            "ASTROGUARD_STREAMING_ENABLED", "false"
        ).strip().lower()

        if enabled_value not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("Invalid ASTROGUARD_STREAMING_ENABLED value")

        enabled = enabled_value in {"true", "1", "yes"}

        return cls(
            enabled=enabled,
            transport=os.getenv(
                "ASTROGUARD_STREAMING_TRANSPORT", "memory"
            ).strip().lower(),
            queue_capacity=int(
                os.getenv("ASTROGUARD_STREAMING_QUEUE_CAPACITY", "256")
            ),
            publish_timeout_seconds=float(
                os.getenv("ASTROGUARD_STREAMING_PUBLISH_TIMEOUT", "5")
            ),
            consumer_batch_size=int(
                os.getenv("ASTROGUARD_STREAMING_BATCH_SIZE", "16")
            ),
        )