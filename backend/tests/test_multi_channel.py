import csv
import json
from pathlib import Path

import numpy as np
import pytest

from astroguard_api.mission_data.multi_channel import (
    AcquisitionError,
    read_label_record,
    validate_array,
)


def make_labels(path: Path, channel="A-1", rows=100):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["chan_id", "spacecraft", "num_values", "anomaly_sequences"],
        )
        writer.writeheader()
        writer.writerow({
            "chan_id": channel,
            "spacecraft": "SMAP",
            "num_values": str(rows),
            "anomaly_sequences": "[[10, 20]]",
        })


def test_label_record_is_parsed(tmp_path):
    path = tmp_path / "labels.csv"
    make_labels(path)
    record = read_label_record(path, "A-1")
    assert record["spacecraft"] == "SMAP"
    assert record["expected_test_rows"] == 100
    assert record["anomaly_sequences"] == [[10, 20]]


def test_missing_label_file_rejected(tmp_path):
    with pytest.raises(AcquisitionError):
        read_label_record(tmp_path / "missing.csv", "A-1")


def test_duplicate_channel_metadata_rejected(tmp_path):
    path = tmp_path / "labels.csv"
    make_labels(path)
    with path.open("a", encoding="utf-8") as stream:
        stream.write('A-1,SMAP,100,"[[10,20]]"\n')
    with pytest.raises(AcquisitionError):
        read_label_record(path, "A-1")


def test_invalid_anomaly_interval_rejected(tmp_path):
    path = tmp_path / "labels.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'chan_id,spacecraft,num_values,anomaly_sequences\n'
        'A-1,SMAP,100,"[[10,120]]"\n',
        encoding="utf-8",
    )
    with pytest.raises(AcquisitionError):
        read_label_record(path, "A-1")


def test_valid_numeric_array(tmp_path):
    path = tmp_path / "valid.npy"
    np.save(path, np.ones((20, 25), dtype=np.float32))
    result = validate_array(path)
    assert result["shape"] == [20, 25]


def test_non_finite_array_rejected(tmp_path):
    path = tmp_path / "invalid.npy"
    values = np.ones((20, 25), dtype=np.float32)
    values[3, 2] = np.nan
    np.save(path, values)
    with pytest.raises(AcquisitionError):
        validate_array(path)


def test_one_dimensional_array_rejected(tmp_path):
    path = tmp_path / "one_dim.npy"
    np.save(path, np.ones(20))
    with pytest.raises(AcquisitionError):
        validate_array(path)


def test_object_array_rejected(tmp_path):
    path = tmp_path / "object.npy"
    np.save(path, np.array([["unsafe"]], dtype=object))
    with pytest.raises(AcquisitionError):
        validate_array(path)
