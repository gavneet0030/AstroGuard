from __future__ import annotations

import hashlib
import json
import os
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .registry import (
    get_channel,
    validate_channel,
    read_source_label,
    RegistryError,
)


class PreprocessingError(RuntimeError):
    """Raised when telemetry preprocessing cannot be completed."""


DEFAULT_WINDOWS = (5, 30)
DEFAULT_CHUNK_ROWS = 2048
SCHEMA_VERSION = "1.0"


def _validate_windows(windows: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(value) for value in windows)

    if not result:
        raise PreprocessingError("At least one rolling window is required")

    if any(value < 2 for value in result):
        raise PreprocessingError("Rolling windows must be >= 2")

    if len(set(result)) != len(result):
        raise PreprocessingError("Rolling windows must be unique")

    return tuple(sorted(result))


def _as_numeric_matrix(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values)

    if array.ndim != 2:
        raise PreprocessingError(f"{name} must be a two-dimensional array")

    if array.shape[0] == 0 or array.shape[1] == 0:
        raise PreprocessingError(f"{name} cannot be empty")

    if array.dtype.kind not in "iuf":
        raise PreprocessingError(f"{name} must contain numeric values")

    if not np.isfinite(array).all():
        raise PreprocessingError(f"{name} contains non-finite values")

    return np.asarray(array, dtype=np.float64)


def _rolling_mean_std(
    values: np.ndarray,
    window: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Causal trailing rolling statistics.

    For row i, the window contains only rows max(0, i-window+1) through i.
    No future observation is used.
    """
    values = np.asarray(values, dtype=np.float64)
    count = values.shape[0]

    cumulative = np.empty(count + 1, dtype=np.float64)
    cumulative_sq = np.empty(count + 1, dtype=np.float64)

    cumulative[0] = 0.0
    cumulative_sq[0] = 0.0

    np.cumsum(values, out=cumulative[1:])
    np.cumsum(values * values, out=cumulative_sq[1:])

    indices = np.arange(count)
    starts = np.maximum(0, indices - window + 1)

    sums = cumulative[indices + 1] - cumulative[starts]
    sums_sq = cumulative_sq[indices + 1] - cumulative_sq[starts]

    counts = indices - starts + 1
    means = sums / counts

    variances = (sums_sq / counts) - (means * means)
    variances = np.maximum(variances, 0.0)

    return means, np.sqrt(variances)


def engineer_features(
    train: np.ndarray,
    test: np.ndarray,
    windows: Sequence[int] = DEFAULT_WINDOWS,
) -> dict[str, Any]:
    """
    Generate features and fit normalization on training data only.

    Feature layout:
      1. Original input columns.
      2. First differences of all input columns.
      3. Rolling mean of input column zero for each window.
      4. Rolling standard deviation of input column zero for each window.

    Rolling windows reset independently for train and test.
    """
    train_values = _as_numeric_matrix(train, "train")
    test_values = _as_numeric_matrix(test, "test")

    if train_values.shape[1] != test_values.shape[1]:
        raise PreprocessingError("Train/test feature counts differ")

    rolling_windows = _validate_windows(windows)

    def create_features(values: np.ndarray) -> np.ndarray:
        # Original source columns.
        blocks = [values]

        # First difference; the first observation has no predecessor.
        differences = np.zeros_like(values, dtype=np.float64)
        differences[1:] = values[1:] - values[:-1]
        blocks.append(differences)

        # Rolling statistics for the target telemetry column (column zero).
        target = values[:, 0]

        for window in rolling_windows:
            rolling_mean, rolling_std = _rolling_mean_std(target, window)
            blocks.append(rolling_mean.reshape(-1, 1))
            blocks.append(rolling_std.reshape(-1, 1))

        output = np.concatenate(blocks, axis=1)

        if not np.isfinite(output).all():
            raise PreprocessingError("Feature generation produced non-finite values")

        return output

    train_features = create_features(train_values)
    test_features = create_features(test_values)

    # Fit scaler exclusively on training features.
    means = np.mean(train_features, axis=0, dtype=np.float64)
    scales = np.std(train_features, axis=0, dtype=np.float64)

    # Constant columns are centered but not divided by zero.
    scales[scales < 1e-12] = 1.0

    train_scaled = ((train_features - means) / scales).astype(np.float32)
    test_scaled = ((test_features - means) / scales).astype(np.float32)

    if not np.isfinite(train_scaled).all():
        raise PreprocessingError("Normalized training features are non-finite")

    if not np.isfinite(test_scaled).all():
        raise PreprocessingError("Normalized test features are non-finite")

    raw_feature_count = train_values.shape[1]

    feature_names = (
        [f"raw_{i:02d}" for i in range(raw_feature_count)]
        + [f"diff_{i:02d}" for i in range(raw_feature_count)]
        + [
            name
            for window in rolling_windows
            for name in (
                f"target_rolling_mean_{window}",
                f"target_rolling_std_{window}",
            )
        ]
    )

    return {
        "train": train_scaled,
        "test": test_scaled,
        "feature_names": feature_names,
        "scaler_mean": means.tolist(),
        "scaler_scale": scales.tolist(),
        "rolling_windows": list(rolling_windows),
        "raw_feature_count": raw_feature_count,
        "engineered_feature_count": len(feature_names),
        "scaler_fit_split": "train",
        "rolling_policy": "causal_trailing_window_reset_per_split",
        "output_dtype": "float32",
    }


def build_anomaly_labels(
    row_count: int,
    anomaly_sequences: Sequence[Sequence[int]],
) -> np.ndarray:
    """
    Build a binary label vector.

    Source anomaly intervals are interpreted as inclusive [start, end].
    """
    if row_count <= 0:
        raise PreprocessingError("row_count must be positive")

    labels = np.zeros(row_count, dtype=np.uint8)

    for interval in anomaly_sequences:
        if len(interval) != 2:
            raise PreprocessingError("Anomaly interval must contain two indices")

        start, end = int(interval[0]), int(interval[1])

        if start < 0 or end < start or end >= row_count:
            raise PreprocessingError(
                f"Anomaly interval [{start}, {end}] is outside test bounds"
            )

        labels[start:end + 1] = 1

    return labels


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _atomic_save_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=path.stem + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    os.close(fd)

    temporary_path = Path(temporary_name)

    try:
        with temporary_path.open("wb") as stream:
            np.save(stream, array, allow_pickle=False)

        os.replace(temporary_path, path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=path.stem + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    os.close(fd)

    temporary_path = Path(temporary_name)

    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def preprocess_channel(
    project_root: Path,
    channel_id: str,
    spacecraft: str = "SMAP",
    windows: Sequence[int] = DEFAULT_WINDOWS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Validate, engineer, normalize and persist one channel.

    Raw source arrays are never modified.
    """
    root = Path(project_root).resolve()

    try:
        record = get_channel(
            root,
            channel_id,
            spacecraft=spacecraft,
        )

        source_validation = validate_channel(
            root,
            record,
            verify_hashes=True,
        )

        source_label = read_source_label(
            root,
            record.spacecraft,
            record.channel_id,
        )

    except RegistryError as exc:
        raise PreprocessingError(str(exc)) from exc

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

    result = engineer_features(train, test, windows=windows)

    labels = build_anomaly_labels(
        row_count=test.shape[0],
        anomaly_sequences=source_label["anomaly_sequences"],
    )

    if labels.shape[0] != result["test"].shape[0]:
        raise PreprocessingError("Test feature and label row counts differ")

    output_dir = (
        root
        / "data"
        / "processed"
        / "telemetry_features"
        / record.spacecraft.lower()
        / record.channel_id.lower()
    )

    output_files = {
        "train_features": output_dir / "train_features.npy",
        "test_features": output_dir / "test_features.npy",
        "test_labels": output_dir / "test_labels.npy",
    }

    manifest_path = output_dir / "preprocessing_manifest.json"

    if manifest_path.exists() and not overwrite:
        raise PreprocessingError(
            f"Processed output already exists: {output_dir}. "
            "Use overwrite=True to replace it."
        )

    for path in output_files.values():
        if path.exists() and not overwrite:
            raise PreprocessingError(
                f"Processed output already exists: {path}"
            )

    _atomic_save_npy(output_files["train_features"], result["train"])
    _atomic_save_npy(output_files["test_features"], result["test"])
    _atomic_save_npy(output_files["test_labels"], labels)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pipeline": "AstroGuard telemetry preprocessing",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "spacecraft": record.spacecraft,
        "channel_id": record.channel_id,
        "source_repository": record.manifest["source_repository"],
        "source_train_sha256": record.manifest["train_sha256"],
        "source_test_sha256": record.manifest["test_sha256"],
        "source_validation": source_validation,
        "train_shape": list(result["train"].shape),
        "test_shape": list(result["test"].shape),
        "labels_shape": list(labels.shape),
        "feature_names": result["feature_names"],
        "raw_feature_count": result["raw_feature_count"],
        "engineered_feature_count": result["engineered_feature_count"],
        "rolling_windows": result["rolling_windows"],
        "rolling_policy": result["rolling_policy"],
        "scaler_fit_split": result["scaler_fit_split"],
        "scaler_mean": result["scaler_mean"],
        "scaler_scale": result["scaler_scale"],
        "output_dtype": result["output_dtype"],
        "anomaly_interval_convention": "inclusive_start_and_end",
        "anomaly_sequences": source_label["anomaly_sequences"],
        "anomaly_row_count": int(labels.sum()),
        "normal_row_count": int(labels.shape[0] - labels.sum()),
        "files": {
            name: {
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for name, path in output_files.items()
        },
        "raw_data_modified": False,
        "test_data_used_for_scaler_fit": False,
        "timestamps_reconstructed": False,
        "physical_units_inferred": False,
    }

    _atomic_write_json(manifest_path, manifest)

    manifest["manifest_path"] = str(manifest_path.relative_to(root))
    manifest["output_directory"] = str(output_dir.relative_to(root))

    return manifest
