from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from astroguard_api.mission_data.registry import (
    RegistryError,
    discover_channels,
    get_channel,
    validate_channel,
)

from astroguard_api.mission_data.unified_loader import (
    TelemetryLoadError,
    inspect_channel,
    list_channels,
    load_channel,
)


REPOSITORY = "appleparan/telemanom"


def digest(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def create_project(tmp_path: Path) -> Path:
    root = tmp_path / "AstroGuard"

    (root / "data/raw/mission_sources/smap_msl").mkdir(
        parents=True,
        exist_ok=True,
    )

    labels = root / "data/raw/mission_sources/smap_msl/labeled_anomalies.csv"

    with labels.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "chan_id",
                "spacecraft",
                "num_values",
                "anomaly_sequences",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "chan_id": "A-1",
            "spacecraft": "SMAP",
            "num_values": 8,
            "anomaly_sequences": "[(2, 3)]",
        })
        writer.writerow({
            "chan_id": "P-1",
            "spacecraft": "SMAP",
            "num_values": 6,
            "anomaly_sequences": "[(1, 2)]",
        })

    return root


def create_channel(
    root: Path,
    channel: str,
    spacecraft: str,
    train_rows: int = 4,
    test_rows: int = 8,
):
    directory = (
        root
        / "data/raw/mission_sources/telemanom_channels"
        / spacecraft.lower()
        / channel.lower()
    )
    directory.mkdir(parents=True, exist_ok=True)

    train = np.arange(
        train_rows * 3,
        dtype=np.float64,
    ).reshape(train_rows, 3)

    test = np.arange(
        test_rows * 3,
        dtype=np.float64,
    ).reshape(test_rows, 3)

    train_path = directory / "train.npy"
    test_path = directory / "test.npy"

    np.save(train_path, train)
    np.save(test_path, test)

    label_intervals = (
        [[2, 3]] if channel == "A-1"
        else [[1, 2]]
    )

    manifest = {
        "schema_version": 1,
        "source_repository": REPOSITORY,
        "channel_id": channel,
        "spacecraft": spacecraft,
        "acquired_at_utc": "2026-11-12T00:00:00+00:00",
        "train": {
            "shape": list(train.shape),
            "dtype": str(train.dtype),
        },
        "test": {
            "shape": list(test.shape),
            "dtype": str(test.dtype),
        },
        "expected_test_rows_from_labels": test_rows,
        "anomaly_sequences": label_intervals,
        "train_sha256": digest(train_path),
        "test_sha256": digest(test_path),
        "train_bytes": train_path.stat().st_size,
        "test_bytes": test_path.stat().st_size,
        "train_url": "https://huggingface.co/example/train.npy",
        "test_url": "https://huggingface.co/example/test.npy",
        "timestamps_reconstructed": False,
        "physical_units_inferred": False,
        "values_are_anonymized_and_pre_scaled": True,
        "validation": {
            "test_rows_match_labels": True,
            "train_test_feature_counts_match": True,
            "all_values_finite": True,
            "sha256_recorded": True,
        },
    }

    (directory / "channel_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return directory


@pytest.fixture
def astroguard_project(tmp_path):
    root = create_project(tmp_path)

    create_channel(
        root,
        "A-1",
        "SMAP",
        train_rows=4,
        test_rows=8,
    )

    create_channel(
        root,
        "P-1",
        "SMAP",
        train_rows=4,
        test_rows=6,
    )

    return root


def test_registry_discovers_two_channels(astroguard_project):
    records = discover_channels(astroguard_project)

    assert len(records) == 2
    assert {record.key for record in records} == {
        "SMAP:A-1",
        "SMAP:P-1",
    }


def test_registry_returns_channel_metadata(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    assert record.channel_id == "A-1"
    assert record.spacecraft == "SMAP"
    assert record.train_shape == (4, 3)
    assert record.test_shape == (8, 3)


def test_registry_validates_hashes_and_labels(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    result = validate_channel(
        astroguard_project,
        record,
        verify_hashes=True,
    )

    assert result["hashes_verified"] is True
    assert result["expected_test_rows"] == 8
    assert result["anomaly_sequences"] == [[2, 3]]


def test_loader_reads_test_split_as_memory_map(astroguard_project):
    loaded = load_channel(
        astroguard_project,
        "A-1",
        split="test",
        spacecraft="SMAP",
    )

    assert loaded.shape == (8, 3)
    assert loaded.feature_count == 3
    assert loaded.is_memory_mapped is True
    assert loaded.values.flags.writeable is False


def test_loader_reads_train_split(astroguard_project):
    loaded = load_channel(
        astroguard_project,
        "A-1",
        split="train",
        spacecraft="SMAP",
    )

    assert loaded.shape == (4, 3)
    assert loaded.split == "train"


def test_loader_rejects_unknown_channel(astroguard_project):
    with pytest.raises(TelemetryLoadError):
        load_channel(
            astroguard_project,
            "UNKNOWN",
            spacecraft="SMAP",
        )


def test_loader_rejects_invalid_split(astroguard_project):
    with pytest.raises(TelemetryLoadError):
        load_channel(
            astroguard_project,
            "A-1",
            split="validation",
            spacecraft="SMAP",
        )


def test_registry_rejects_checksum_mismatch(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    manifest = json.loads(
        record.manifest_path.read_text(encoding="utf-8")
    )
    manifest["train_sha256"] = "0" * 64

    record.manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError):
        refreshed = get_channel(
            astroguard_project,
            "A-1",
            spacecraft="SMAP",
        )
        validate_channel(
            astroguard_project,
            refreshed,
            verify_hashes=True,
        )


def test_registry_rejects_label_row_mismatch(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    manifest = json.loads(
        record.manifest_path.read_text(encoding="utf-8")
    )
    manifest["expected_test_rows_from_labels"] = 999

    record.manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    refreshed = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    with pytest.raises(RegistryError):
        validate_channel(
            astroguard_project,
            refreshed,
            verify_hashes=False,
        )


def test_registry_rejects_non_finite_array(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    array = np.load(record.test_path)
    array[0, 0] = np.nan
    np.save(record.test_path, array)

    refreshed = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    with pytest.raises(RegistryError):
        validate_channel(
            astroguard_project,
            refreshed,
            verify_hashes=False,
        )


def test_registry_rejects_wrong_manifest_identity(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    manifest = json.loads(
        record.manifest_path.read_text(encoding="utf-8")
    )
    manifest["channel_id"] = "P-1"

    record.manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError):
        discover_channels(astroguard_project)


def test_loader_list_returns_registry_entries(astroguard_project):
    entries = list_channels(astroguard_project)

    assert len(entries) == 2
    assert entries[0]["key"] == "SMAP:A-1"
    assert entries[1]["key"] == "SMAP:P-1"


def test_inspect_channel_returns_provenance(astroguard_project):
    result = inspect_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    assert result["source_repository"] == REPOSITORY
    assert result["timestamps_reconstructed"] is False
    assert result["physical_units_inferred"] is False
    assert result["values_are_anonymized_and_pre_scaled"] is True


def test_loader_rejects_writeable_memory_mode(astroguard_project):
    with pytest.raises(TelemetryLoadError):
        load_channel(
            astroguard_project,
            "A-1",
            spacecraft="SMAP",
            mmap_mode="r+",
        )


def test_registry_rejects_wrong_source_repository(astroguard_project):
    record = get_channel(
        astroguard_project,
        "A-1",
        spacecraft="SMAP",
    )

    manifest = json.loads(
        record.manifest_path.read_text(encoding="utf-8")
    )
    manifest["source_repository"] = "untrusted/unknown"

    record.manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(RegistryError):
        discover_channels(astroguard_project)