from __future__ import annotations

import csv
import json

from pathlib import Path

import pytest

from astroguard_api.telemetry.models import (
    TelemetryRecord,
    TelemetryValidationError,
)

from astroguard_api.telemetry.ingestion import (
    IngestionError,
    TelemetryIngestor,
    sha256_file,
)


def valid_record():
    return {
        "timestamp": "2026-01-01T10:00:00Z",
        "channel": "BATTERY_VOLTAGE",
        "value": "28.25",
        "unit": "V",
        "quality": "GOOD",
        "source": "TEST_FIXTURE",
    }


def write_csv(path: Path, rows):
    fields = [
        "timestamp",
        "channel",
        "value",
        "unit",
        "quality",
        "source",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)

    return path


def test_valid_record_normalization():
    record = TelemetryRecord.from_mapping(
        valid_record()
    )

    assert record.channel == "BATTERY_VOLTAGE"
    assert record.value == 28.25
    assert record.unit == "V"
    assert record.quality == "GOOD"
    assert record.timestamp == "2026-01-01T10:00:00Z"


def test_channel_normalization():
    row = valid_record()
    row["channel"] = "battery_voltage"

    record = TelemetryRecord.from_mapping(row)

    assert record.channel == "BATTERY_VOLTAGE"


def test_naive_timestamp_rejected():
    row = valid_record()
    row["timestamp"] = "2026-01-01T10:00:00"

    with pytest.raises(TelemetryValidationError):
        TelemetryRecord.from_mapping(row)


def test_invalid_channel_rejected():
    row = valid_record()
    row["channel"] = "battery voltage"

    with pytest.raises(TelemetryValidationError):
        TelemetryRecord.from_mapping(row)


@pytest.mark.parametrize(
    "value",
    [
        "not-a-number",
        "NaN",
        "Infinity",
        "-Infinity",
        True,
        None,
    ],
)
def test_invalid_numeric_values_rejected(value):
    row = valid_record()
    row["value"] = value

    with pytest.raises(TelemetryValidationError):
        TelemetryRecord.from_mapping(row)


def test_fingerprint_is_deterministic():
    first = TelemetryRecord.from_mapping(valid_record())
    second = TelemetryRecord.from_mapping(valid_record())

    assert first.fingerprint() == second.fingerprint()


def test_csv_ingestion_accepts_valid_records(tmp_path):
    source = write_csv(
        tmp_path / "telemetry.csv",
        [
            valid_record(),
            {
                **valid_record(),
                "timestamp": "2026-01-01T10:01:00Z",
                "value": "28.10",
            },
        ],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(
        source,
        source_label="TEST_FIXTURE",
    )

    assert result.status == "completed"
    assert result.total_records == 2
    assert result.accepted_records == 2
    assert result.rejected_records == 0
    assert result.duplicate_records == 0


def test_invalid_records_are_quarantined(tmp_path):
    invalid = valid_record()
    invalid["value"] = "not-numeric"

    source = write_csv(
        tmp_path / "mixed.csv",
        [
            valid_record(),
            invalid,
        ],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    assert result.accepted_records == 1
    assert result.rejected_records == 1

    quarantine = Path(result.quarantine_path).read_text(
        encoding="utf-8"
    )

    assert "value must be numeric" in quarantine


def test_duplicate_records_are_deduplicated(tmp_path):
    row = valid_record()

    source = write_csv(
        tmp_path / "duplicates.csv",
        [row, row, row],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    assert result.total_records == 3
    assert result.accepted_records == 1
    assert result.duplicate_records == 2


def test_raw_archive_checksum_matches_source(tmp_path):
    source = write_csv(
        tmp_path / "source.csv",
        [valid_record()],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    archived = Path(result.raw_archive_path)

    assert archived.exists()
    assert sha256_file(archived) == result.source_sha256
    assert sha256_file(source) == result.source_sha256


def test_same_file_is_idempotent(tmp_path):
    source = write_csv(
        tmp_path / "idempotent.csv",
        [valid_record()],
    )

    ingestor = TelemetryIngestor(tmp_path)

    first = ingestor.ingest_file(source)
    second = ingestor.ingest_file(source)

    assert first.status == "completed"
    assert second.status == "already_processed"
    assert first.batch_id == second.batch_id
    assert first.processed_path == second.processed_path


def test_manifest_contains_provenance(tmp_path):
    source = write_csv(
        tmp_path / "manifest.csv",
        [valid_record()],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    manifest = json.loads(
        Path(result.manifest_path).read_text(
            encoding="utf-8"
        )
    )

    assert manifest["source_sha256"] == result.source_sha256
    assert manifest["total_records"] == 1
    assert manifest["accepted_records"] == 1
    assert manifest["pipeline"] == (
        "astroguard-telemetry-ingestion"
    )


def test_json_array_ingestion(tmp_path):
    source = tmp_path / "telemetry.json"

    source.write_text(
        json.dumps([valid_record()]),
        encoding="utf-8",
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    assert result.accepted_records == 1
    assert result.rejected_records == 0


def test_json_records_object_ingestion(tmp_path):
    source = tmp_path / "telemetry_object.json"

    source.write_text(
        json.dumps(
            {
                "records": [
                    valid_record(),
                ]
            }
        ),
        encoding="utf-8",
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    assert result.accepted_records == 1


def test_json_non_object_record_is_quarantined(tmp_path):
    source = tmp_path / "invalid_json_record.json"

    source.write_text(
        json.dumps(
            [
                valid_record(),
                123,
            ]
        ),
        encoding="utf-8",
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    assert result.accepted_records == 1
    assert result.rejected_records == 1


def test_unsupported_extension_rejected(tmp_path):
    source = tmp_path / "telemetry.txt"
    source.write_text("invalid", encoding="utf-8")

    with pytest.raises(IngestionError):
        TelemetryIngestor(tmp_path).ingest_file(source)


def test_empty_source_rejected(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("", encoding="utf-8")

    with pytest.raises(IngestionError):
        TelemetryIngestor(tmp_path).ingest_file(source)


def test_missing_source_rejected(tmp_path):
    source = tmp_path / "missing.csv"

    with pytest.raises(IngestionError):
        TelemetryIngestor(tmp_path).ingest_file(source)


def test_raw_source_is_not_modified(tmp_path):
    source = write_csv(
        tmp_path / "immutable.csv",
        [valid_record()],
    )

    original_hash = sha256_file(source)

    TelemetryIngestor(tmp_path).ingest_file(source)

    assert sha256_file(source) == original_hash


def test_processed_output_is_valid_jsonl(tmp_path):
    source = write_csv(
        tmp_path / "output.csv",
        [valid_record()],
    )

    result = TelemetryIngestor(tmp_path).ingest_file(source)

    lines = Path(result.processed_path).read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 1

    record = json.loads(lines[0])

    assert record["channel"] == "BATTERY_VOLTAGE"
    assert record["value"] == 28.25
