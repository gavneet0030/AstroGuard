from __future__ import annotations

import csv
import json

import pytest

from pathlib import Path

from astroguard_api.mission_sources.smap_msl import (
    EXPECTED_TOTAL_CHANNELS,
    LABELS_URL,
    SOURCE_ID,
    SourceConnectorError,
    SmapMslSource,
)


def write_csv(path: Path, rows: list[dict]) -> Path:
    columns = [
        "chan_id",
        "spacecraft",
        "anomaly_sequences",
        "class",
        "num_values",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
        )

        writer.writeheader()
        writer.writerows(rows)

    return path


def valid_row(**overrides):
    row = {
        "chan_id": "A-1",
        "spacecraft": "SMAP",
        "anomaly_sequences": "[[10, 15], [20, 25]]",
        "class": "point",
        "num_values": "100",
    }

    row.update(overrides)
    return row


def test_source_metadata_is_registered():
    metadata = SmapMslSource.metadata()

    assert metadata.source_id == SOURCE_ID
    assert metadata.channel_count == EXPECTED_TOTAL_CHANNELS
    assert metadata.anomaly_sequence_count == 105
    assert set(metadata.spacecraft) == {"SMAP", "MSL"}


def test_source_url_is_https():
    assert LABELS_URL.startswith("https://")


def test_discovery_does_not_download(tmp_path):
    source = SmapMslSource(tmp_path)

    result = source.discover()

    assert result["downloaded"] is False
    assert result["channel_count"] == 82


def test_anomaly_interval_parser_json():
    result = SmapMslSource._parse_anomaly_sequences(
        "[[1, 5], [10, 15]]"
    )

    assert result == [[1, 5], [10, 15]]


def test_anomaly_interval_parser_legacy():
    result = SmapMslSource._parse_anomaly_sequences(
        "[[1, 5], [10, 15]]"
    )

    assert result == [[1, 5], [10, 15]]


def test_empty_anomaly_list():
    assert SmapMslSource._parse_anomaly_sequences("[]") == []


@pytest.mark.parametrize(
    "value",
    [
        "[[-1, 5]]",
        "[[10, 5]]",
        "[[1, 2, 3]]",
        "[[1, true]]",
        "__import__('os').system('whoami')",
        "not-a-list",
    ],
)
def test_invalid_anomaly_intervals_rejected(value):
    with pytest.raises(SourceConnectorError):
        SmapMslSource._parse_anomaly_sequences(value)


def test_valid_label_csv(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row()],
    )

    rows = SmapMslSource.read_labels(path)

    assert len(rows) == 1
    assert rows[0]["channel_id"] == "A-1"
    assert rows[0]["spacecraft"] == "SMAP"
    assert rows[0]["anomaly_sequences"] == [
        [10, 15],
        [20, 25],
    ]


def test_anomaly_indices_are_preserved(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row()],
    )

    row = SmapMslSource.read_labels(path)[0]

    assert row["anomaly_sequences"][0] == [10, 15]
    assert row["timestamp_available"] is False


def test_no_fabricated_timestamp(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row()],
    )

    row = SmapMslSource.read_labels(path)[0]

    assert row["timestamp_available"] is False
    assert row["index_semantics"] == (
        "zero_based_sample_index_in_test_stream"
    )


def test_no_physical_unit_inference(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row()],
    )

    row = SmapMslSource.read_labels(path)[0]

    assert row["physical_unit_available"] is False


def test_malformed_spacecraft_rejected(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row(spacecraft="UNKNOWN")],
    )

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_invalid_channel_id_rejected(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row(chan_id="../../unsafe")],
    )

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_invalid_sample_count_rejected(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [valid_row(num_values="0")],
    )

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_interval_outside_stream_rejected(tmp_path):
    path = write_csv(
        tmp_path / "labels.csv",
        [
            valid_row(
                anomaly_sequences="[[10, 150]]",
                num_values="100",
            )
        ],
    )

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_missing_column_rejected(tmp_path):
    path = tmp_path / "bad.csv"

    path.write_text(
        "chan_id,spacecraft\nA-1,SMAP\n",
        encoding="utf-8",
    )

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_empty_file_rejected(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(path)


def test_missing_file_rejected(tmp_path):
    with pytest.raises(SourceConnectorError):
        SmapMslSource.read_labels(
            tmp_path / "missing.csv"
        )


def test_duplicate_channel_ids_are_preserved_as_distinct_records(tmp_path):
    path = write_csv(
        tmp_path / "duplicate.csv",
        [
            valid_row(
                anomaly_sequences="[[10, 20]]",
                num_values="100",
            ),
            valid_row(
                anomaly_sequences="[[30, 40]]",
                num_values="100",
            ),
        ],
    )

    rows = SmapMslSource.read_labels(path)

    assert len(rows) == 2

    assert rows[0]["channel_id"] == "A-1"
    assert rows[1]["channel_id"] == "A-1"

    assert rows[0]["record_id"] != rows[1]["record_id"]

    assert rows[0]["anomaly_sequences"] == [[10, 20]]
    assert rows[1]["anomaly_sequences"] == [[30, 40]]


def test_duplicate_channel_validation_metadata(tmp_path):
    path = write_csv(
        tmp_path / "duplicate_metadata.csv",
        [
            valid_row(
                anomaly_sequences="[[10, 20]]",
                num_values="100",
            ),
            valid_row(
                anomaly_sequences="[[30, 40]]",
                num_values="100",
            ),
        ],
    )

    result = SmapMslSource.validate_labels(path)

    assert result["channel_count"] == 2
    assert result["source_record_count"] == 2
    assert result["unique_channel_id_count"] == 1

    assert result["repeated_channel_records"] == {
        "SMAP/A-1": 2
    }

    assert result["repeated_channel_record_count"] == 1


def test_record_identity_contains_original_row_number(tmp_path):
    path = write_csv(
        tmp_path / "record_identity.csv",
        [
            valid_row(),
            valid_row(
                anomaly_sequences="[[30, 40]]",
            ),
        ],
    )

    rows = SmapMslSource.read_labels(path)

    assert rows[0]["source_row_number"] == 2
    assert rows[1]["source_row_number"] == 3

    assert rows[0]["record_id"].endswith("row-2")
    assert rows[1]["record_id"].endswith("row-3")


def test_manifest_records_duplicate_channel_information(tmp_path):
    source = SmapMslSource(tmp_path)

    write_csv(
        source.labels_path,
        [
            valid_row(
                anomaly_sequences="[[10, 20]]",
                num_values="100",
            ),
            valid_row(
                anomaly_sequences="[[30, 40]]",
                num_values="100",
            ),
        ],
    )

    validation = source.validate_labels(
        source.labels_path
    )

    manifest_path = source.write_manifest(validation)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    details = manifest["validation"]

    assert details["source_record_count"] == 2
    assert details["unique_channel_id_count"] == 1
    assert details["repeated_channel_records"]["SMAP/A-1"] == 2


def test_manifest_written(tmp_path):
    source = SmapMslSource(tmp_path)

    source.labels_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_csv(
        source.labels_path,
        [valid_row()],
    )

    validation = source.validate_labels(
        source.labels_path
    )

    manifest_path = source.write_manifest(
        validation
    )

    assert manifest_path.exists()

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    assert manifest["source"]["source_id"] == SOURCE_ID
    assert manifest["validation"]["channel_count"] == 1
    assert manifest["retrieval"]["labels_sha256"]


def test_manifest_records_limitations(tmp_path):
    source = SmapMslSource(tmp_path)

    write_csv(
        source.labels_path,
        [valid_row()],
    )

    validation = source.validate_labels(
        source.labels_path
    )

    manifest_path = source.write_manifest(
        validation
    )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    limitations = manifest["limitations"]

    assert any("timestamps" in item for item in limitations)
    assert any("units" in item for item in limitations)


def test_url_allowlist_rejects_unknown_url():
    with pytest.raises(SourceConnectorError):
        SmapMslSource._validate_download_url(
            "https://example.com/evil.csv"
        )


def test_download_is_not_triggered_by_discovery(tmp_path):
    source = SmapMslSource(tmp_path)

    source.discover()

    assert not source.labels_path.exists()


def test_sha256_is_deterministic(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("astroguard", encoding="utf-8")

    first = SmapMslSource.sha256_file(path)
    second = SmapMslSource.sha256_file(path)

    assert first == second
    assert len(first) == 64
