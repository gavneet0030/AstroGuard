from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TELEMANOM_REPOSITORY = "https://github.com/khundman/telemanom"

LABELS_URL = (
    "https://raw.githubusercontent.com/"
    "khundman/telemanom/master/labeled_anomalies.csv"
)

SOURCE_ID = "NASA_SMAP_MSL_TELEMANOM"

EXPECTED_SPACECRAFT = {
    "SMAP",
    "MSL",
}

EXPECTED_CHANNEL_COUNTS = {
    "SMAP": 55,
    "MSL": 27,
}

EXPECTED_TOTAL_CHANNELS = 82
EXPECTED_TOTAL_ANOMALY_SEQUENCES = 105

MAX_LABEL_FILE_BYTES = 5 * 1024 * 1024

REQUIRED_COLUMNS = {
    "chan_id",
    "spacecraft",
    "anomaly_sequences",
    "class",
    "num_values",
}


class SourceConnectorError(Exception):
    """Raised when a mission source cannot be safely processed."""


@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    source_name: str
    spacecraft: tuple[str, ...]
    channel_count: int
    anomaly_sequence_count: int
    repository_url: str
    labels_url: str
    data_characteristics: tuple[str, ...]
    provenance_classification: str
    timestamp_policy: str
    unit_policy: str


@dataclass(frozen=True)
class DatasetSource:
    metadata: SourceMetadata

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.metadata)


class SmapMslSource:
    """
    Connector for the published SMAP/MSL telemetry anomaly benchmark.

    Important data limitations:

    - Channel IDs are anonymized.
    - Original mission timestamps are anonymized.
    - Telemetry values are pre-scaled.
    - Anomaly labels refer to sample-index intervals.
    - Physical units must not be inferred from scaled values.

    This module retrieves and validates the anomaly metadata.
    It does not claim to reconstruct original flight telemetry.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()

        self.raw_root = (
            self.project_root
            / "data"
            / "raw"
            / "mission_sources"
            / "smap_msl"
        )

        self.metadata_root = (
            self.project_root
            / "data"
            / "processed"
            / "mission_metadata"
        )

        self.labels_path = (
            self.raw_root
            / "labeled_anomalies.csv"
        )

        self.manifest_path = (
            self.metadata_root
            / "smap_msl_source_manifest.json"
        )

        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.metadata_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def metadata() -> SourceMetadata:
        return SourceMetadata(
            source_id=SOURCE_ID,
            source_name="NASA SMAP and MSL spacecraft anomaly benchmark",
            spacecraft=("SMAP", "MSL"),
            channel_count=EXPECTED_TOTAL_CHANNELS,
            anomaly_sequence_count=EXPECTED_TOTAL_ANOMALY_SEQUENCES,
            repository_url=TELEMANOM_REPOSITORY,
            labels_url=LABELS_URL,
            data_characteristics=(
                "anonymized_channel_identifiers",
                "anonymized_timestamps",
                "pre_scaled_telemetry_values",
                "sample_index_based_anomaly_labels",
                "training_and_test_splits",
            ),
            provenance_classification=(
                "NASA_mission_derived_research_benchmark"
            ),
            timestamp_policy=(
                "preserve_sample_indices; never fabricate UTC timestamps"
            ),
            unit_policy=(
                "preserve_scaled_values; do not infer physical units"
            ),
        )

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as stream:
            for chunk in iter(
                lambda: stream.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _validate_download_url(url: str) -> None:
        if url != LABELS_URL:
            raise SourceConnectorError(
                "URL is not in the approved source registry."
            )

        if not url.startswith("https://"):
            raise SourceConnectorError(
                "Only HTTPS sources are accepted."
            )

    def download_labels(
        self,
        timeout_seconds: int = 30,
        force: bool = False,
    ) -> Path:
        """
        Download the original anomaly-label CSV.

        A temporary file is used so interrupted downloads do not
        leave a partially written final file.
        """

        self._validate_download_url(LABELS_URL)

        if self.labels_path.exists() and not force:
            self.validate_labels(self.labels_path)
            return self.labels_path

        request = urllib.request.Request(
            LABELS_URL,
            headers={
                "User-Agent": "AstroGuard-Research-Connector/1.0",
                "Accept": "text/csv,*/*",
            },
        )

        temporary_path: Path | None = None

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:

                final_url = response.geturl()

                if not final_url.startswith("https://"):
                    raise SourceConnectorError(
                        "Source redirected to a non-HTTPS URL."
                    )

                content_length = response.headers.get(
                    "Content-Length"
                )

                if content_length is not None:
                    declared_size = int(content_length)

                    if declared_size > MAX_LABEL_FILE_BYTES:
                        raise SourceConnectorError(
                            "Label file exceeds the configured size limit."
                        )

                descriptor, temporary_name = tempfile.mkstemp(
                    prefix="astroguard_smap_msl_",
                    suffix=".part",
                    dir=str(self.raw_root),
                )

                os.close(descriptor)
                temporary_path = Path(temporary_name)

                total_bytes = 0

                with temporary_path.open("wb") as output:
                    while True:
                        chunk = response.read(64 * 1024)

                        if not chunk:
                            break

                        total_bytes += len(chunk)

                        if total_bytes > MAX_LABEL_FILE_BYTES:
                            raise SourceConnectorError(
                                "Downloaded label file exceeds size limit."
                            )

                        output.write(chunk)

            if total_bytes == 0:
                raise SourceConnectorError(
                    "Downloaded label file is empty."
                )

            self.validate_labels(temporary_path)

            temporary_path.replace(self.labels_path)
            temporary_path = None

            return self.labels_path

        except urllib.error.URLError as exc:
            raise SourceConnectorError(
                f"Unable to retrieve anomaly labels: {exc}"
            ) from exc

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _parse_anomaly_sequences(
        raw_value: str,
    ) -> list[list[int]]:
        """
        Parse the published CSV representation of anomaly intervals.

        The field contains a Python-like list representation.
        JSON parsing is attempted first. A restricted parser is used
        for the single-quoted legacy representation.
        """

        value = (raw_value or "").strip()

        if not value:
            return []

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None

        if parsed is None:
            # Do not use eval() or exec() on dataset content.
            #
            # Accepted syntax:
            # [[start, end], [start, end]]
            #
            if not re.fullmatch(
                r"\s*\[\s*(?:\[\s*\d+\s*,\s*\d+\s*\]"
                r"(?:\s*,\s*\[\s*\d+\s*,\s*\d+\s*\])*)?\s*\]\s*",
                value,
            ):
                raise SourceConnectorError(
                    "Anomaly interval field has an unsupported format."
                )

            numbers = [
                int(item)
                for item in re.findall(r"\d+", value)
            ]

            if len(numbers) % 2 != 0:
                raise SourceConnectorError(
                    "Anomaly interval has an odd number of indices."
                )

            parsed = [
                numbers[index:index + 2]
                for index in range(0, len(numbers), 2)
            ]

        if not isinstance(parsed, list):
            raise SourceConnectorError(
                "Anomaly intervals must be a list."
            )

        result: list[list[int]] = []

        for interval in parsed:
            if (
                not isinstance(interval, list)
                or len(interval) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    for value in interval
                )
            ):
                raise SourceConnectorError(
                    "Each anomaly interval must contain two integer indices."
                )

            start, end = interval

            if start < 0 or end < start:
                raise SourceConnectorError(
                    "Anomaly interval boundaries are invalid."
                )

            result.append([start, end])

        return result

    @classmethod
    def read_labels(
        cls,
        path: str | Path,
    ) -> list[dict[str, Any]]:
        label_path = Path(path)

        if not label_path.exists():
            raise SourceConnectorError(
                f"Label file does not exist: {label_path}"
            )

        if label_path.stat().st_size == 0:
            raise SourceConnectorError(
                "Label file is empty."
            )

        if label_path.stat().st_size > MAX_LABEL_FILE_BYTES:
            raise SourceConnectorError(
                "Label file exceeds configured size limit."
            )

        rows: list[dict[str, Any]] = []

        try:
            with label_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as stream:

                reader = csv.DictReader(stream)

                if reader.fieldnames is None:
                    raise SourceConnectorError(
                        "CSV header is missing."
                    )

                normalized_headers = {
                    str(column).strip().lower()
                    for column in reader.fieldnames
                }

                missing = REQUIRED_COLUMNS - normalized_headers

                if missing:
                    raise SourceConnectorError(
                        "Missing required columns: "
                        + ", ".join(sorted(missing))
                    )

                for line_number, raw_row in enumerate(
                    reader,
                    start=2,
                ):
                    row = {
                        str(key).strip().lower(): value
                        for key, value in raw_row.items()
                        if key is not None
                    }

                    spacecraft = (
                        row.get("spacecraft") or ""
                    ).strip().upper()

                    channel = (
                        row.get("chan_id") or ""
                    ).strip()

                    if spacecraft not in EXPECTED_SPACECRAFT:
                        raise SourceConnectorError(
                            f"Unknown spacecraft on line {line_number}."
                        )

                    if not re.fullmatch(
                        r"[A-Za-z0-9_-]{1,64}",
                        channel,
                    ):
                        raise SourceConnectorError(
                            f"Invalid channel ID on line {line_number}."
                        )

                    try:
                        num_values = int(
                            row.get("num_values") or ""
                        )
                    except ValueError as exc:
                        raise SourceConnectorError(
                            f"Invalid num_values on line {line_number}."
                        ) from exc

                    if num_values < 1:
                        raise SourceConnectorError(
                            f"Invalid stream length on line {line_number}."
                        )

                    sequences = cls._parse_anomaly_sequences(
                        row.get("anomaly_sequences") or ""
                    )

                    for start, end in sequences:
                        if end >= num_values:
                            raise SourceConnectorError(
                                f"Anomaly interval exceeds stream length "
                                f"on line {line_number}."
                            )

                    rows.append({
                        "record_id": (
                            f"{spacecraft}:{channel}:row-{line_number}"
                        ),
                        "source_row_number": line_number,
                        "channel_id": channel,
                        "spacecraft": spacecraft,
                        "anomaly_sequences": sequences,
                        "anomaly_class": (
                            row.get("class") or ""
                        ).strip(),
                        "num_values": num_values,
                        "index_semantics": (
                            "zero_based_sample_index_in_test_stream"
                        ),
                        "timestamp_available": False,
                        "physical_unit_available": False,
                    })

        except UnicodeDecodeError as exc:
            raise SourceConnectorError(
                "Label file is not valid UTF-8."
            ) from exc

        if not rows:
            raise SourceConnectorError(
                "No label records were found."
            )

        # Channel identifiers are not globally unique in this
        # published source file. Preserve every source row.
        #
        # Row identity is based on spacecraft, channel ID and
        # original source row number.
        #
        # Do not deduplicate anomaly records by channel ID.

        record_ids = [
            row["record_id"]
            for row in rows
        ]

        if len(record_ids) != len(set(record_ids)):
            raise SourceConnectorError(
                "Duplicate source record identities detected."
            )

        return rows

    @classmethod
    def validate_labels(
        cls,
        path: str | Path,
    ) -> dict[str, Any]:
        rows = cls.read_labels(path)

        spacecraft_counts: dict[str, int] = {}
        anomaly_count = 0
        sample_count = 0

        channel_occurrences: dict[str, int] = {}

        for row in rows:
            spacecraft = row["spacecraft"]

            spacecraft_counts[spacecraft] = (
                spacecraft_counts.get(spacecraft, 0) + 1
            )

            channel_key = (
                f"{spacecraft}/{row['channel_id']}"
            )

            channel_occurrences[channel_key] = (
                channel_occurrences.get(channel_key, 0) + 1
            )

            anomaly_count += len(
                row["anomaly_sequences"]
            )

            sample_count += row["num_values"]

        repeated_channels = {
            channel: count
            for channel, count in channel_occurrences.items()
            if count > 1
        }

        unique_channel_count = len(channel_occurrences)

        return {
            "valid": True,
            "channel_count": len(rows),
            "source_record_count": len(rows),
            "unique_channel_id_count": unique_channel_count,
            "repeated_channel_records": repeated_channels,
            "repeated_channel_record_count": sum(
                count - 1
                for count in repeated_channels.values()
            ),
            "spacecraft_channel_counts": spacecraft_counts,
            "anomaly_sequence_count": anomaly_count,
            "declared_sample_count": sample_count,
            "channels": rows,
        }

    def write_manifest(
        self,
        validation: dict[str, Any],
    ) -> Path:
        if not self.labels_path.exists():
            raise SourceConnectorError(
                "Cannot write manifest without downloaded labels."
            )

        source = self.metadata()

        manifest = {
            "schema_version": "1.0",
            "source": asdict(source),
            "retrieval": {
                "retrieved_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "labels_file": str(self.labels_path),
                "labels_sha256": self.sha256_file(
                    self.labels_path
                ),
                "labels_file_size_bytes": (
                    self.labels_path.stat().st_size
                ),
            },
            "validation": {
                "valid": validation["valid"],
                "channel_count": validation["channel_count"],
                "source_record_count": (
                    validation["source_record_count"]
                ),
                "unique_channel_id_count": (
                    validation["unique_channel_id_count"]
                ),
                "repeated_channel_records": (
                    validation["repeated_channel_records"]
                ),
                "repeated_channel_record_count": (
                    validation["repeated_channel_record_count"]
                ),
                "spacecraft_channel_counts": (
                    validation["spacecraft_channel_counts"]
                ),
                "anomaly_sequence_count": (
                    validation["anomaly_sequence_count"]
                ),
                "declared_sample_count": (
                    validation["declared_sample_count"]
                ),
            },
            "limitations": [
                "Channel identifiers are anonymized.",
                "Mission timestamps are anonymized.",
                "Telemetry values are pre-scaled.",
                "Anomaly labels are sample-index intervals.",
                "Physical units are not inferred.",
                "This benchmark is not an operational flight feed.",
            ],
        }

        self.manifest_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.manifest_path.with_suffix(
            ".json.tmp"
        )

        temporary.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary.replace(self.manifest_path)

        return self.manifest_path

    def discover(self) -> dict[str, Any]:
        metadata = self.metadata()

        return {
            "source_id": metadata.source_id,
            "source_name": metadata.source_name,
            "spacecraft": list(metadata.spacecraft),
            "channel_count": metadata.channel_count,
            "expected_channel_counts": (
                EXPECTED_CHANNEL_COUNTS
            ),
            "anomaly_sequence_count": (
                metadata.anomaly_sequence_count
            ),
            "repository_url": metadata.repository_url,
            "labels_url": metadata.labels_url,
            "provenance_classification": (
                metadata.provenance_classification
            ),
            "data_characteristics": list(
                metadata.data_characteristics
            ),
            "timestamp_policy": metadata.timestamp_policy,
            "unit_policy": metadata.unit_policy,
            "downloaded": self.labels_path.exists(),
        }

    def run(self, force_download: bool = False) -> dict[str, Any]:
        labels_path = self.download_labels(
            force=force_download
        )

        validation = self.validate_labels(
            labels_path
        )

        manifest_path = self.write_manifest(
            validation
        )

        return {
            "status": "completed",
            "source_id": SOURCE_ID,
            "labels_path": str(labels_path),
            "manifest_path": str(manifest_path),
            "labels_sha256": self.sha256_file(
                labels_path
            ),
            "channel_count": validation["channel_count"],
            "spacecraft_channel_counts": (
                validation["spacecraft_channel_counts"]
            ),
            "anomaly_sequence_count": (
                validation["anomaly_sequence_count"]
            ),
            "declared_sample_count": (
                validation["declared_sample_count"]
            ),
            "timestamp_reconstruction": False,
            "physical_unit_inference": False,
        }
