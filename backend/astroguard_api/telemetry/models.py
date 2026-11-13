"""
Validated telemetry record model.

The canonical record format is intentionally independent of
any particular spacecraft mission or archive provider.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


CHANNEL_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9_]{0,63}$"
)

QUALITY_VALUES = {
    "GOOD",
    "SUSPECT",
    "BAD",
    "UNKNOWN",
}


class TelemetryValidationError(ValueError):
    """Invalid telemetry record."""


def parse_timestamp(value: Any) -> str:
    if value is None:
        raise TelemetryValidationError(
            "timestamp is required"
        )

    raw = str(value).strip()

    if not raw:
        raise TelemetryValidationError(
            "timestamp is empty"
        )

    normalized = raw.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TelemetryValidationError(
            "timestamp must be a valid ISO-8601 datetime"
        ) from exc

    if parsed.tzinfo is None:
        raise TelemetryValidationError(
            "timestamp must include a timezone"
        )

    return (
        parsed.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_numeric_value(value: Any) -> float:
    if value is None:
        raise TelemetryValidationError(
            "value is required"
        )

    if isinstance(value, bool):
        raise TelemetryValidationError(
            "boolean values are not valid telemetry measurements"
        )

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TelemetryValidationError(
            "value must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise TelemetryValidationError(
            "value must be finite"
        )

    return number


@dataclass(frozen=True)
class TelemetryRecord:
    timestamp: str
    channel: str
    value: float
    unit: str = ""
    quality: str = "UNKNOWN"
    source: str = "UNSPECIFIED"

    @classmethod
    def from_mapping(
        cls,
        row: Mapping[str, Any],
        *,
        default_source: str = "UNSPECIFIED",
    ) -> "TelemetryRecord":

        if not isinstance(row, Mapping):
            raise TelemetryValidationError(
                "record must be an object"
            )

        timestamp = parse_timestamp(
            row.get("timestamp")
        )

        channel = str(
            row.get("channel", "")
        ).strip().upper()

        if not CHANNEL_PATTERN.fullmatch(channel):
            raise TelemetryValidationError(
                "channel must match the uppercase channel identifier format"
            )

        value = parse_numeric_value(
            row.get("value")
        )

        unit = str(
            row.get("unit") or ""
        ).strip()

        if len(unit) > 32:
            raise TelemetryValidationError(
                "unit exceeds 32 characters"
            )

        quality = str(
            row.get("quality") or "UNKNOWN"
        ).strip().upper()

        if quality not in QUALITY_VALUES:
            raise TelemetryValidationError(
                "quality must be GOOD, SUSPECT, BAD, or UNKNOWN"
            )

        source = str(
            row.get("source") or default_source
        ).strip()

        if not source:
            source = "UNSPECIFIED"

        if len(source) > 200:
            raise TelemetryValidationError(
                "source exceeds 200 characters"
            )

        return cls(
            timestamp=timestamp,
            channel=channel,
            value=value,
            unit=unit,
            quality=quality,
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "channel": self.channel,
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality,
            "source": self.source,
        }

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
