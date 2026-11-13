from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from sqlalchemy.orm import Mapped, mapped_column

from astroguard_api.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class TelemetryRecord(Base):

    __tablename__ = "telemetry_records"

    __table_args__ = (
        Index(
            "ix_telemetry_channel_timestamp",
            "channel",
            "event_timestamp",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="api",
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ExperimentRun(Base):

    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    experiment_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created",
    )

    configuration: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    metrics: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ModelArtifact(Base):

    __tablename__ = "model_artifacts"

    __table_args__ = (
        UniqueConstraint(
            "channel",
            "model_name",
            "version",
            name="uq_model_channel_name_version",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    model_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    artifact_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class InferenceEvent(Base):

    __tablename__ = "inference_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    model_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    prediction: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    anomaly_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    input_fingerprint: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AuditEvent(Base):

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    event_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="system",
    )

    resource_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )