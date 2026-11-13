import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from astroguard_api.mission_data.telemanom_channel import (
    ChannelAcquisitionError,
    download_bounded,
    find_channel_records,
    inventory,
    load_label_records,
    validate_npy,
)


def create_labels(path: Path, rows: list[dict]) -> Path:
    fields = [
        "chan_id",
        "spacecraft",
        "num_values",
        "anomaly_sequences",
        "class",
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


def row(
    channel="P-1",
    spacecraft="SMAP",
    num_values=100,
    sequences="[[10, 20]]",
):
    return {
        "chan_id": channel,
        "spacecraft": spacecraft,
        "num_values": str(num_values),
        "anomaly_sequences": sequences,
        "class": "point",
    }


def test_label_inventory_preserves_duplicate_channel_rows(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [
            row(
                channel="P-2",
                sequences="[[5350, 6575]]",
                num_values=8209,
            ),
            row(
                channel="P-2",
                sequences="[[5300, 6420]]",
                num_values=8209,
            ),
        ],
    )

    result = inventory(path)

    assert result["source_record_count"] == 2
    assert result["unique_channel_count"] == 1
    assert len(result["channels"]["P-2"]) == 2
    assert result["duplicate_channel_records"]["P-2"] == 2


def test_find_channel_returns_both_duplicate_rows(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [
            row(channel="P-2"),
            row(channel="P-2"),
        ],
    )

    records = find_channel_records(path, "P-2")

    assert len(records) == 2
    assert records[0].record_id != records[1].record_id


def test_label_loader_reads_single_record(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [row()],
    )

    records = load_label_records(path)

    assert len(records) == 1
    assert records[0].channel_id == "P-1"
    assert records[0].spacecraft == "SMAP"
    assert records[0].num_values == 100
    assert records[0].anomaly_sequences == [[10, 20]]


def test_invalid_interval_rejected(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [row(sequences="[[20, 10]]")],
    )

    with pytest.raises(ChannelAcquisitionError):
        load_label_records(path)


def test_interval_outside_stream_rejected(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [row(sequences="[[10, 100]]", num_values=100)],
    )

    with pytest.raises(ChannelAcquisitionError):
        load_label_records(path)


def test_validate_npy_accepts_valid_array(tmp_path):
    path = tmp_path / "test.npy"

    np.save(
        path,
        np.ones((100, 25), dtype=np.float32),
    )

    result = validate_npy(
        path,
        expected_rows=100,
    )

    assert result["shape"] == [100, 25]
    assert result["target_feature_index"] == 0
    assert result["command_feature_count"] == 24
    assert result["finite_values"] is True
    assert result["expected_rows_match"] is True


def test_validate_npy_rejects_wrong_row_count(tmp_path):
    path = tmp_path / "test.npy"

    np.save(
        path,
        np.ones((99, 25), dtype=np.float32),
    )

    with pytest.raises(ChannelAcquisitionError):
        validate_npy(path, expected_rows=100)


def test_validate_npy_rejects_nan(tmp_path):
    path = tmp_path / "test.npy"

    array = np.ones((10, 3), dtype=np.float32)
    array[4, 1] = np.nan

    np.save(path, array)

    with pytest.raises(ChannelAcquisitionError):
        validate_npy(path)


def test_validate_npy_rejects_infinity(tmp_path):
    path = tmp_path / "test.npy"

    array = np.ones((10, 3), dtype=np.float32)
    array[4, 1] = np.inf

    np.save(path, array)

    with pytest.raises(ChannelAcquisitionError):
        validate_npy(path)


def test_validate_npy_rejects_one_dimensional_array(tmp_path):
    path = tmp_path / "test.npy"

    np.save(
        path,
        np.ones((10,), dtype=np.float32),
    )

    with pytest.raises(ChannelAcquisitionError):
        validate_npy(path)


def test_validate_npy_rejects_object_dtype(tmp_path):
    path = tmp_path / "test.npy"

    np.save(
        path,
        np.array([["a", "b"]], dtype=object),
    )

    with pytest.raises(ChannelAcquisitionError):
        validate_npy(path)


def test_download_rejects_unapproved_source(tmp_path):
    with pytest.raises(ChannelAcquisitionError):
        download_bounded(
            "https://example.com/file.npy",
            tmp_path / "file.npy",
        )


def test_sha256_is_correct(tmp_path):
    path = tmp_path / "test.npy"

    np.save(
        path,
        np.ones((10, 2), dtype=np.float32),
    )

    result = validate_npy(path)

    expected = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    assert result["sha256"] == expected


def test_manifest_limitation_fields_round_trip(tmp_path):
    payload = {
        "timestamps_reconstructed": False,
        "physical_units_inferred": False,
        "telemetry_values_anonymized": True,
        "values_pre_scaled": True,
    }

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    loaded = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert loaded == payload


def test_invalid_channel_id_rejected(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [row()],
    )

    with pytest.raises(ChannelAcquisitionError):
        find_channel_records(path, "../P-1")


def test_invalid_spacecraft_filter_rejected(tmp_path):
    path = create_labels(
        tmp_path / "labels.csv",
        [row()],
    )

    with pytest.raises(ChannelAcquisitionError):
        find_channel_records(
            path,
            "P-1",
            "UNKNOWN",
        )
