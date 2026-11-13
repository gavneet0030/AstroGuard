"""
AstroGuard telemetry data engineering package.

This package provides mission-independent telemetry ingestion.
It does not claim that any input file originates from NASA.
"""

from astroguard_api.telemetry.models import (
    TelemetryRecord,
    TelemetryValidationError,
)

from astroguard_api.telemetry.ingestion import (
    IngestionResult,
    TelemetryIngestor,
)

__all__ = [
    "TelemetryRecord",
    "TelemetryValidationError",
    "IngestionResult",
    "TelemetryIngestor",
]
