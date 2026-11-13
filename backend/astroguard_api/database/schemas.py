from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Channel = Literal["a-1", "p-1"]


class TelemetryRecordCreate(BaseModel):

    channel: Channel

    event_timestamp: datetime

    source: str = Field(
        default="api",
        min_length=1,
        max_length=128,
    )

    payload: dict[str, Any] = Field(min_length=1)

    @field_validator("event_timestamp")
    @classmethod
    def validate_timestamp(cls, value):

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include timezone information.")

        return value


class TelemetryRecordRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    event_timestamp: datetime
    source: str
    payload: dict[str, Any]
    created_at: datetime


class ExperimentCreate(BaseModel):

    channel: Channel

    experiment_name: str = Field(
        min_length=2,
        max_length=160,
    )

    configuration: dict[str, Any] = Field(default_factory=dict)

    notes: str | None = Field(
        default=None,
        max_length=4000,
    )


class ExperimentRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    experiment_name: str
    status: str
    configuration: dict[str, Any]
    metrics: dict[str, Any]
    notes: str | None
    created_at: datetime
    completed_at: datetime | None


class ModelArtifactCreate(BaseModel):

    channel: Channel

    model_name: str = Field(min_length=2, max_length=120)

    version: str = Field(min_length=1, max_length=64)

    artifact_path: str = Field(min_length=1, max_length=1000)

    checksum_sha256: str = Field(
        pattern=r"^[a-fA-F0-9]{64}$"
    )

    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ModelArtifactRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    model_name: str
    version: str
    artifact_path: str
    checksum_sha256: str
    metadata_json: dict[str, Any]
    is_active: bool
    created_at: datetime


class InferenceEventCreate(BaseModel):

    channel: Channel

    model_name: str = Field(min_length=2, max_length=120)

    model_version: str | None = Field(
        default=None,
        max_length=64,
    )

    prediction: int = Field(ge=0, le=1)

    anomaly_score: float = Field(
        ge=0.0,
        le=1.0e12,
    )

    input_fingerprint: str | None = Field(
        default=None,
        max_length=128,
    )


class InferenceEventRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    model_name: str
    model_version: str | None
    prediction: int
    anomaly_score: float
    input_fingerprint: str | None
    created_at: datetime