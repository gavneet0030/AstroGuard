from __future__ import annotations

import ast
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_REPOSITORY = "appleparan/telemanom"
SUPPORTED_SPACECRAFT = {"SMAP", "MSL"}
SUPPORTED_SCHEMA_VERSION = 1

LABELS_RELATIVE_PATH = Path(
    "data/raw/mission_sources/smap_msl/labeled_anomalies.csv"
)

CHANNELS_RELATIVE_PATH = Path(
    "data/raw/mission_sources/telemanom_channels"
)


class RegistryError(RuntimeError):
    """Raised when channel registry metadata or artifacts are invalid."""


@dataclass(frozen=True)
class ChannelRecord:
    spacecraft: str
    channel_id: str
    channel_directory: Path
    manifest_path: Path
    train_path: Path
    test_path: Path
    manifest: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.spacecraft}:{self.channel_id}"

    @property
    def source_repository(self) -> str:
        return str(self.manifest["source_repository"])

    @property
    def train_shape(self) -> tuple[int, ...]:
        return tuple(self.manifest["train"]["shape"])

    @property
    def test_shape(self) -> tuple[int, ...]:
        return tuple(self.manifest["test"]["shape"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RegistryError(f"Manifest not found: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"Invalid manifest JSON: {path}") from exc

    if not isinstance(value, dict):
        raise RegistryError("Manifest root must be a JSON object")

    return value


def _validate_manifest_identity(
    manifest: dict[str, Any],
    spacecraft: str,
    channel_id: str,
) -> None:
    if manifest.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise RegistryError(
            f"Unsupported manifest schema version: "
            f"{manifest.get('schema_version')!r}"
        )

    if manifest.get("source_repository") != EXPECTED_REPOSITORY:
        raise RegistryError(
            f"Unexpected source repository: "
            f"{manifest.get('source_repository')!r}"
        )

    if manifest.get("channel_id") != channel_id:
        raise RegistryError(
            f"Manifest channel mismatch: expected {channel_id!r}, "
            f"found {manifest.get('channel_id')!r}"
        )

    if manifest.get("spacecraft") != spacecraft:
        raise RegistryError(
            f"Manifest spacecraft mismatch: expected {spacecraft!r}, "
            f"found {manifest.get('spacecraft')!r}"
        )

    if spacecraft not in SUPPORTED_SPACECRAFT:
        raise RegistryError(f"Unsupported spacecraft: {spacecraft}")


def _validate_manifest_structure(
    manifest: dict[str, Any],
) -> None:
    required = {
        "schema_version",
        "source_repository",
        "channel_id",
        "spacecraft",
        "acquired_at_utc",
        "train",
        "test",
        "expected_test_rows_from_labels",
        "anomaly_sequences",
        "train_sha256",
        "test_sha256",
        "train_bytes",
        "test_bytes",
        "train_url",
        "test_url",
        "timestamps_reconstructed",
        "physical_units_inferred",
        "values_are_anonymized_and_pre_scaled",
        "validation",
    }

    missing = required - set(manifest)

    if missing:
        raise RegistryError(
            f"Manifest missing required fields: {sorted(missing)}"
        )

    for split in ("train", "test"):
        metadata = manifest[split]

        if not isinstance(metadata, dict):
            raise RegistryError(f"Manifest {split} metadata must be an object")

        shape = metadata.get("shape")

        if not isinstance(shape, list) or len(shape) != 2:
            raise RegistryError(f"Manifest {split} shape must have 2 dimensions")

        if any(
            not isinstance(value, int) or value <= 0
            for value in shape
        ):
            raise RegistryError(f"Manifest {split} shape contains invalid values")

        if not isinstance(metadata.get("dtype"), str):
            raise RegistryError(f"Manifest {split} dtype must be a string")

    if not isinstance(manifest["expected_test_rows_from_labels"], int):
        raise RegistryError("expected_test_rows_from_labels must be an integer")

    for field in ("train_sha256", "test_sha256"):
        value = manifest[field]

        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value.lower())
        ):
            raise RegistryError(f"Invalid SHA-256 field: {field}")

    if not isinstance(manifest["validation"], dict):
        raise RegistryError("Manifest validation must be an object")


def read_source_label(
    project_root: Path,
    spacecraft: str,
    channel_id: str,
) -> dict[str, Any]:
    labels_path = project_root / LABELS_RELATIVE_PATH

    if not labels_path.is_file():
        raise RegistryError(f"Source label CSV missing: {labels_path}")

    try:
        with labels_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            reader = csv.DictReader(stream)

            required = {
                "chan_id",
                "spacecraft",
                "num_values",
                "anomaly_sequences",
            }

            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise RegistryError("Source label CSV missing required columns")

            matches = [
                row for row in reader
                if row["chan_id"].strip().upper() == channel_id.upper()
                and row["spacecraft"].strip().upper() == spacecraft.upper()
            ]

    except OSError as exc:
        raise RegistryError("Unable to read source label CSV") from exc

    if len(matches) != 1:
        raise RegistryError(
            f"Expected one label record for {spacecraft}/{channel_id}; "
            f"found {len(matches)}"
        )

    row = matches[0]

    try:
        expected_rows = int(row["num_values"])
        intervals = ast.literal_eval(row["anomaly_sequences"])
    except (ValueError, SyntaxError, TypeError) as exc:
        raise RegistryError("Invalid source label metadata") from exc

    if expected_rows <= 0:
        raise RegistryError("Source label row count must be positive")

    if not isinstance(intervals, list):
        raise RegistryError("Anomaly sequences must be a list")

    clean_intervals = []

    for interval in intervals:
        if (
            not isinstance(interval, (list, tuple))
            or len(interval) != 2
        ):
            raise RegistryError("Invalid anomaly interval structure")

        start, end = interval

        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end < start
            or end >= expected_rows
        ):
            raise RegistryError("Anomaly interval outside declared test stream")

        clean_intervals.append([start, end])

    return {
        "spacecraft": spacecraft.upper(),
        "channel_id": channel_id.upper(),
        "expected_test_rows": expected_rows,
        "anomaly_sequences": clean_intervals,
    }


def _record_from_directory(
    project_root: Path,
    spacecraft: str,
    channel_directory: Path,
) -> ChannelRecord:
    manifest_path = channel_directory / "channel_manifest.json"
    train_path = channel_directory / "train.npy"
    test_path = channel_directory / "test.npy"

    manifest = load_manifest(manifest_path)

    channel_id = str(manifest.get("channel_id", "")).strip().upper()

    if not channel_id:
        raise RegistryError(f"Missing channel identity in {manifest_path}")

    _validate_manifest_identity(manifest, spacecraft, channel_id)
    _validate_manifest_structure(manifest)

    expected_directory = (
        project_root
        / CHANNELS_RELATIVE_PATH
        / spacecraft.lower()
        / channel_id.lower()
    )

    if channel_directory.resolve() != expected_directory.resolve():
        raise RegistryError(
            f"Channel directory does not match manifest identity: "
            f"{channel_directory}"
        )

    for path in (train_path, test_path):
        if not path.is_file():
            raise RegistryError(f"Channel artifact missing: {path}")

    return ChannelRecord(
        spacecraft=spacecraft,
        channel_id=channel_id,
        channel_directory=channel_directory,
        manifest_path=manifest_path,
        train_path=train_path,
        test_path=test_path,
        manifest=manifest,
    )


def discover_channels(
    project_root: Path,
) -> list[ChannelRecord]:
    project_root = Path(project_root).resolve()
    base = project_root / CHANNELS_RELATIVE_PATH

    if not base.is_dir():
        raise RegistryError(f"Channel registry directory missing: {base}")

    records: list[ChannelRecord] = []

    for spacecraft in sorted(SUPPORTED_SPACECRAFT):
        spacecraft_dir = base / spacecraft.lower()

        if not spacecraft_dir.exists():
            continue

        if not spacecraft_dir.is_dir():
            raise RegistryError(
                f"Spacecraft path is not a directory: {spacecraft_dir}"
            )

        for channel_directory in sorted(spacecraft_dir.iterdir()):
            if not channel_directory.is_dir():
                continue

            manifest_path = channel_directory / "channel_manifest.json"

            # A directory without a manifest is not an acquired channel.
            if not manifest_path.is_file():
                continue

            record = _record_from_directory(
                project_root,
                spacecraft,
                channel_directory,
            )

            records.append(record)

    keys = [record.key for record in records]

    if len(keys) != len(set(keys)):
        raise RegistryError("Duplicate spacecraft/channel registry identity")

    return sorted(
        records,
        key=lambda item: (item.spacecraft, item.channel_id),
    )


def get_channel(
    project_root: Path,
    channel_id: str,
    spacecraft: str | None = None,
) -> ChannelRecord:
    channel_id = channel_id.strip().upper()

    if not channel_id:
        raise RegistryError("Channel ID cannot be empty")

    requested_spacecraft = (
        spacecraft.strip().upper() if spacecraft else None
    )

    if requested_spacecraft and requested_spacecraft not in SUPPORTED_SPACECRAFT:
        raise RegistryError(
            f"Unsupported spacecraft: {requested_spacecraft}"
        )

    matches = [
        record for record in discover_channels(project_root)
        if record.channel_id == channel_id
        and (
            requested_spacecraft is None
            or record.spacecraft == requested_spacecraft
        )
    ]

    if not matches:
        raise RegistryError(
            f"Channel not registered: {requested_spacecraft or '*'}:{channel_id}"
        )

    if len(matches) > 1:
        raise RegistryError(
            f"Channel ID {channel_id} is ambiguous across spacecraft; "
            "specify spacecraft explicitly"
        )

    return matches[0]


def validate_channel(
    project_root: Path,
    record: ChannelRecord,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    import numpy as np

    manifest = record.manifest

    label = read_source_label(
        project_root,
        record.spacecraft,
        record.channel_id,
    )

    train = np.load(
        record.train_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    test = np.load(
        record.test_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    if train.ndim != 2 or test.ndim != 2:
        raise RegistryError("Telemetry arrays must be two-dimensional")

    if tuple(train.shape) != tuple(manifest["train"]["shape"]):
        raise RegistryError("Train array shape does not match manifest")

    if tuple(test.shape) != tuple(manifest["test"]["shape"]):
        raise RegistryError("Test array shape does not match manifest")

    if train.shape[1] != test.shape[1]:
        raise RegistryError("Train/test feature counts do not match")

    if str(train.dtype) != manifest["train"]["dtype"]:
        raise RegistryError("Train dtype does not match manifest")

    if str(test.dtype) != manifest["test"]["dtype"]:
        raise RegistryError("Test dtype does not match manifest")

    # Phase 2.2.2.1:
    # Validate all telemetry values without loading complete arrays into RAM.
    # Arrays are memory-mapped read-only and scanned in bounded row chunks.
    for split_name, array in (("train", train), ("test", test)):
        for start in range(0, array.shape[0], 2048):
            block = np.asarray(array[start:start + 2048])

            if not np.isfinite(block).all():
                raise RegistryError(
                    f"{split_name.capitalize()} array contains non-finite values"
                )

    if test.shape[0] != label["expected_test_rows"]:
        raise RegistryError("Test rows do not match source labels")

    if (
        manifest["expected_test_rows_from_labels"]
        != label["expected_test_rows"]
    ):
        raise RegistryError("Manifest label row count is stale or inconsistent")

    if manifest["anomaly_sequences"] != label["anomaly_sequences"]:
        raise RegistryError("Manifest anomaly intervals do not match source labels")

    if record.train_path.stat().st_size != manifest["train_bytes"]:
        raise RegistryError("Train file size does not match manifest")

    if record.test_path.stat().st_size != manifest["test_bytes"]:
        raise RegistryError("Test file size does not match manifest")

    if verify_hashes:
        if sha256_file(record.train_path) != manifest["train_sha256"]:
            raise RegistryError("Train SHA-256 does not match manifest")

        if sha256_file(record.test_path) != manifest["test_sha256"]:
            raise RegistryError("Test SHA-256 does not match manifest")

    return {
        "key": record.key,
        "channel_id": record.channel_id,
        "spacecraft": record.spacecraft,
        "source_repository": record.source_repository,
        "train_shape": list(train.shape),
        "test_shape": list(test.shape),
        "train_dtype": str(train.dtype),
        "test_dtype": str(test.dtype),
        "train_sha256": manifest["train_sha256"],
        "test_sha256": manifest["test_sha256"],
        "expected_test_rows": label["expected_test_rows"],
        "anomaly_sequences": label["anomaly_sequences"],
        "hashes_verified": verify_hashes,
        "timestamps_reconstructed": manifest["timestamps_reconstructed"],
        "physical_units_inferred": manifest["physical_units_inferred"],
        "values_are_anonymized_and_pre_scaled": (
            manifest["values_are_anonymized_and_pre_scaled"]
        ),
    }