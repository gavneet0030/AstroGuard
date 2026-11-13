"""Versioned, validated event contracts for AstroGuard streaming."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventEnvelope(BaseModel):
    """
    Standard event envelope.

    payload contains domain-specific event data.
    event_id supports downstream idempotency.
    occurred_at must be timezone-aware.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    event_id: UUID = Field(default_factory=uuid4)

    event_type: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_.-]*$",
    )

    schema_version: int = Field(default=1, ge=1, le=100)

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    source: str = Field(
        min_length=1,
        max_length=128,
    )

    channel: str | None = Field(
        default=None,
        pattern=r"^(a-1|p-1)$",
    )

    partition_key: str | None = Field(
        default=None,
        max_length=256,
    )

    payload: dict[str, Any]

    @field_validator("occurred_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("payload must be a JSON object")
        return value