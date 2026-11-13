from __future__ import annotations

import hashlib
import json
import os
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


FEATURE_NAMES = (
    "target_first_difference",
    "target_absolute_difference",
    "target_percentage_change",
    "target_rolling_mean_w5",
    "target_rolling_std_w5",
    "target_rolling_min_w5",
    "target_rolling_max_w5",
    "target_rolling_median_w5",
    "target_rolling_mad_w5",
    "target_rolling_mean_w30",
    "target_rolling_std_w30",
    "target_rolling_min_w30",
    "target_rolling_max_w30",
    "target_ewma_alpha_01",
    "target_ewma_alpha_03",
)

FEATURE_COUNT = len(FEATURE_NAMES)
BASELINE_FEATURE_COUNT = 54
EXPECTED_TOTAL_FEATURES = BASELINE_FEATURE_COUNT + FEATURE_COUNT
TARGET_FEATURE_INDEX = 0

WINDOWS = (5, 30)
EPSILON = 1e-8


class AdvancedFeatureError(RuntimeError):
    """Raised when advanced feature engineering cannot be completed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def atomic_save_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=path.stem + ".",
        suffix=".npy.tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(fd, "wb") as stream:
            np.save(stream, array, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=path.stem + ".",
        suffix=".json.tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _validate_signal(signal: np.ndarray) -> np.ndarray:
    array = np.asarray(signal)

    if array.ndim != 1:
        raise AdvancedFeatureError("Target signal must be one-dimensional")

    if array.size == 0:
        raise AdvancedFeatureError("Target signal cannot be empty")

    if array.dtype.kind not in "iuf":
        raise AdvancedFeatureError("Target signal must be numeric")

    array = np.asarray(array, dtype=np.float64)

    if not np.isfinite(array).all():
        raise AdvancedFeatureError("Target signal contains non-finite values")

    return array


def _rolling_statistics(
    signal: np.ndarray,
    window: int,
) -> tuple[np.ndarray, ...]:
    """
    Causal trailing-window statistics.

    Each row uses only the current sample and preceding samples.
    At the beginning of a split, the window uses available history.
    """

    if window <= 0:
        raise AdvancedFeatureError("Window must be positive")

    count = len(signal)

    means = np.empty(count, dtype=np.float64)
    stds = np.empty(count, dtype=np.float64)
    minima = np.empty(count, dtype=np.float64)
    maxima = np.empty(count, dtype=np.float64)
    medians = np.empty(count, dtype=np.float64)
    mads = np.empty(count, dtype=np.float64)

    for index in range(count):
        start = max(0, index - window + 1)
        sample = signal[start:index + 1]

        means[index] = np.mean(sample)
        stds[index] = np.std(sample, ddof=0)
        minima[index] = np.min(sample)
        maxima[index] = np.max(sample)

        median = np.median(sample)
        medians[index] = median
        mads[index] = np.median(np.abs(sample - median))

    return means, stds, minima, maxima, medians, mads


def _ewma(signal: np.ndarray, alpha: float) -> np.ndarray:
    if not 0.0 < alpha <= 1.0:
        raise AdvancedFeatureError("EWMA alpha must be in (0, 1]")

    output = np.empty(len(signal), dtype=np.float64)

    output[0] = signal[0]

    for index in range(1, len(signal)):
        output[index] = (
            alpha * signal[index]
            + (1.0 - alpha) * output[index - 1]
        )

    return output


def build_temporal_features(signal: np.ndarray) -> np.ndarray:
    """
    Build 15 causal features from target telemetry column 0.

    No future sample is accessed by any feature.
    """

    values = _validate_signal(signal)
    count = len(values)

    difference = np.zeros(count, dtype=np.float64)

    if count > 1:
        difference[1:] = values[1:] - values[:-1]

    absolute_difference = np.abs(difference)

    percentage_change = np.zeros(count, dtype=np.float64)

    if count > 1:
        denominator = np.maximum(
            np.abs(values[:-1]),
            EPSILON,
        )

        percentage_change[1:] = (
            difference[1:] / denominator
        )

    w5 = _rolling_statistics(values, 5)
    w30 = _rolling_statistics(values, 30)

    ewma_01 = _ewma(values, 0.1)
    ewma_03 = _ewma(values, 0.3)

    features = np.column_stack((
        difference,
        absolute_difference,
        percentage_change,

        w5[0],
        w5[1],
        w5[2],
        w5[3],
        w5[4],
        w5[5],

        w30[0],
        w30[1],
        w30[2],
        w30[3],

        ewma_01,
        ewma_03,
    ))

    if features.shape != (count, FEATURE_COUNT):
        raise AdvancedFeatureError(
            f"Unexpected feature shape: {features.shape}"
        )

    if not np.isfinite(features).all():
        raise AdvancedFeatureError("Generated temporal features are non-finite")

    return np.asarray(features, dtype=np.float64)


def fit_train_scaler(
    train_features: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    train = np.asarray(train_features, dtype=np.float64)

    if train.ndim != 2 or train.shape[1] != FEATURE_COUNT:
        raise AdvancedFeatureError("Invalid training feature matrix")

    if not np.isfinite(train).all():
        raise AdvancedFeatureError("Training features contain non-finite values")

    mean = np.mean(train, axis=0)
    scale = np.std(train, axis=0, ddof=0)

    # Constant columns are retained as zero after scaling.
    scale = np.where(scale < EPSILON, 1.0, scale)

    return mean, scale


def apply_train_scaler(
    features: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    values = np.asarray(features, dtype=np.float64)

    if values.ndim != 2 or values.shape[1] != FEATURE_COUNT:
        raise AdvancedFeatureError("Invalid feature matrix")

    if mean.shape != (FEATURE_COUNT,) or scale.shape != (FEATURE_COUNT,):
        raise AdvancedFeatureError("Invalid scaler parameter dimensions")

    result = (values - mean) / scale

    if not np.isfinite(result).all():
        raise AdvancedFeatureError("Scaled features contain non-finite values")

    return np.asarray(result, dtype=np.float32)


def _load_array(path: Path) -> np.ndarray:
    if not path.is_file():
        raise AdvancedFeatureError(f"Required input missing: {path}")

    array = np.load(path, mmap_mode="r", allow_pickle=False)

    if array.ndim != 2:
        raise AdvancedFeatureError(f"Expected 2D array: {path}")

    if array.dtype.kind not in "iuf":
        raise AdvancedFeatureError(f"Non-numeric array: {path}")

    for start in range(0, array.shape[0], 2048):
        if not np.isfinite(array[start:start + 2048]).all():
            raise AdvancedFeatureError(f"Non-finite values in {path}")

    return array


def _load_baseline(path: Path, expected_rows: int) -> np.ndarray:
    if not path.is_file():
        raise AdvancedFeatureError(f"Baseline output missing: {path}")

    matrix = np.load(path, mmap_mode="r", allow_pickle=False)

    if matrix.ndim != 2:
        raise AdvancedFeatureError("Baseline matrix must be 2D")

    if matrix.shape != (expected_rows, BASELINE_FEATURE_COUNT):
        raise AdvancedFeatureError(
            f"Expected baseline shape "
            f"({expected_rows}, {BASELINE_FEATURE_COUNT}), "
            f"found {matrix.shape}"
        )

    if matrix.dtype != np.float32:
        raise AdvancedFeatureError("Baseline feature dtype must be float32")

    return matrix


def _load_labels(path: Path, expected_rows: int) -> np.ndarray:
    if not path.is_file():
        raise AdvancedFeatureError(f"Label file missing: {path}")

    labels = np.load(path, mmap_mode="r", allow_pickle=False)

    if labels.shape != (expected_rows,):
        raise AdvancedFeatureError("Label count does not match test rows")

    if labels.dtype != np.uint8:
        raise AdvancedFeatureError("Labels must have uint8 dtype")

    if not np.isin(labels, (0, 1)).all():
        raise AdvancedFeatureError("Labels must contain only 0 and 1")

    return np.asarray(labels)


def _manifest_file(path: Path) -> dict:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_advanced_dataset(
    project_root: str | Path,
    channel_id: str,
    spacecraft: str = "SMAP",
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Build a separate 69-column dataset.

    Existing 54-column baseline files remain untouched.
    """

    from astroguard_api.mission_data.registry import (
        get_channel,
        validate_channel,
    )

    root = Path(project_root).resolve()
    channel = channel_id.strip().upper()
    craft = spacecraft.strip().upper()

    if channel not in {"A-1", "P-1"}:
        raise AdvancedFeatureError("Only acquired pilot channels A-1 and P-1 are supported")

    record = get_channel(root, channel, spacecraft=craft)

    registry_result = validate_channel(
        root,
        record,
        verify_hashes=True,
    )

    raw_dir = (
        root / "data/raw/mission_sources/telemanom_channels"
        / craft.lower() / channel.lower()
    )

    baseline_dir = (
        root / "data/processed/telemetry_features"
        / craft.lower() / channel.lower()
    )

    output_dir = (
        root / "data/processed/advanced_telemetry_features"
        / craft.lower() / channel.lower()
    )

    output_files = {
        "train": output_dir / "train_features_advanced.npy",
        "test": output_dir / "test_features_advanced.npy",
        "labels": output_dir / "test_labels.npy",
        "manifest": output_dir / "advanced_feature_manifest.json",
    }

    if output_dir.exists() and not overwrite:
        raise AdvancedFeatureError(
            f"Output already exists: {output_dir}. "
            "Use overwrite=True after backing it up."
        )

    raw_train_path = raw_dir / "train.npy"
    raw_test_path = raw_dir / "test.npy"

    baseline_train_path = baseline_dir / "train_features.npy"
    baseline_test_path = baseline_dir / "test_features.npy"
    labels_path = baseline_dir / "test_labels.npy"
    baseline_manifest_path = baseline_dir / "preprocessing_manifest.json"

    raw_train = _load_array(raw_train_path)
    raw_test = _load_array(raw_test_path)

    if raw_train.shape[1] <= TARGET_FEATURE_INDEX:
        raise AdvancedFeatureError("Target feature index is unavailable")

    if raw_test.shape[1] <= TARGET_FEATURE_INDEX:
        raise AdvancedFeatureError("Target feature index is unavailable")

    baseline_train = _load_baseline(
        baseline_train_path,
        raw_train.shape[0],
    )

    baseline_test = _load_baseline(
        baseline_test_path,
        raw_test.shape[0],
    )

    labels = _load_labels(labels_path, raw_test.shape[0])

    if not baseline_manifest_path.is_file():
        raise AdvancedFeatureError("Baseline preprocessing manifest missing")

    baseline_manifest = json.loads(
        baseline_manifest_path.read_text(encoding="utf-8-sig")
    )

    if baseline_manifest.get("engineered_feature_count") != BASELINE_FEATURE_COUNT:
        raise AdvancedFeatureError("Baseline manifest feature count mismatch")

    print(f"[INFO] Building advanced features for {craft}/{channel}")
    print(f"[INFO] Raw train shape: {raw_train.shape}")
    print(f"[INFO] Raw test shape: {raw_test.shape}")
    print(f"[INFO] Baseline feature count: {BASELINE_FEATURE_COUNT}")

    train_temporal = build_temporal_features(
        np.asarray(raw_train[:, TARGET_FEATURE_INDEX])
    )

    test_temporal = build_temporal_features(
        np.asarray(raw_test[:, TARGET_FEATURE_INDEX])
    )

    mean, scale = fit_train_scaler(train_temporal)

    train_temporal_scaled = apply_train_scaler(
        train_temporal,
        mean,
        scale,
    )

    test_temporal_scaled = apply_train_scaler(
        test_temporal,
        mean,
        scale,
    )

    train_output = np.concatenate(
        (
            np.asarray(baseline_train),
            train_temporal_scaled,
        ),
        axis=1,
    ).astype(np.float32, copy=False)

    test_output = np.concatenate(
        (
            np.asarray(baseline_test),
            test_temporal_scaled,
        ),
        axis=1,
    ).astype(np.float32, copy=False)

    if train_output.shape[1] != EXPECTED_TOTAL_FEATURES:
        raise AdvancedFeatureError("Unexpected advanced train feature count")

    if test_output.shape[1] != EXPECTED_TOTAL_FEATURES:
        raise AdvancedFeatureError("Unexpected advanced test feature count")

    if not np.isfinite(train_output).all():
        raise AdvancedFeatureError("Advanced train matrix is non-finite")

    if not np.isfinite(test_output).all():
        raise AdvancedFeatureError("Advanced test matrix is non-finite")

    # Ensure existing output directory is not overwritten accidentally.
    output_dir.mkdir(parents=True, exist_ok=True)

    atomic_save_npy(output_files["train"], train_output)
    atomic_save_npy(output_files["test"], test_output)
    atomic_save_npy(output_files["labels"], labels)

    feature_names = (
        list(baseline_manifest["feature_names"])
        + list(FEATURE_NAMES)
    )

    if len(feature_names) != EXPECTED_TOTAL_FEATURES:
        raise AdvancedFeatureError("Feature name count does not match matrix")

    manifest = {
        "schema_version": 1,
        "phase": "2.3.1",
        "channel_id": channel,
        "spacecraft": craft,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),

        "source_repository": "appleparan/telemanom",

        "baseline_feature_count": BASELINE_FEATURE_COUNT,
        "advanced_feature_count": FEATURE_COUNT,
        "total_feature_count": EXPECTED_TOTAL_FEATURES,

        "feature_names": feature_names,
        "advanced_feature_names": list(FEATURE_NAMES),

        "target_feature_index": TARGET_FEATURE_INDEX,
        "target_feature_description": (
            "Target telemetry column 0 from anonymized pre-scaled source arrays"
        ),

        "rolling_windows": list(WINDOWS),
        "rolling_semantics": "causal_trailing_window",
        "window_initialization": "available_history_from_split_start",
        "train_test_window_reset": True,

        "percentage_change_epsilon": EPSILON,
        "percentage_change_definition": (
            "current_minus_previous divided by max(abs(previous), epsilon)"
        ),

        "ewma_alpha_values": [0.1, 0.3],

        "scaler": {
            "method": "training_split_mean_std",
            "fit_split": "train",
            "test_data_used_for_fit": False,
            "mean": mean.tolist(),
            "scale": scale.tolist(),
            "constant_column_scale_fallback": 1.0,
        },

        "label_integrity": {
            "copied_from_phase_2_3_0": True,
            "anomaly_rows": int(labels.sum()),
            "normal_rows": int(len(labels) - labels.sum()),
            "label_dtype": str(labels.dtype),
        },

        "train_shape": list(train_output.shape),
        "test_shape": list(test_output.shape),
        "labels_shape": list(labels.shape),

        "train_dtype": str(train_output.dtype),
        "test_dtype": str(test_output.dtype),

        "raw_data_modified": False,
        "baseline_data_modified": False,
        "timestamps_reconstructed": False,
        "physical_units_inferred": False,
        "source_values_remain_anonymized_and_pre_scaled": True,

        "registry_validation": {
            "channel": record.channel_id,
            "spacecraft": record.spacecraft,
            "hashes_verified": True,
        },

        "input_files": {
            "raw_train": _manifest_file(raw_train_path),
            "raw_test": _manifest_file(raw_test_path),
            "baseline_train": _manifest_file(baseline_train_path),
            "baseline_test": _manifest_file(baseline_test_path),
            "baseline_labels": _manifest_file(labels_path),
            "baseline_manifest": _manifest_file(baseline_manifest_path),
        },

        "files": {
            "train_features": _manifest_file(output_files["train"]),
            "test_features": _manifest_file(output_files["test"]),
            "test_labels": _manifest_file(output_files["labels"]),
        },

        "output_directory": str(output_dir),
    }

    atomic_write_json(output_files["manifest"], manifest)

    # Reload and independently verify persisted artifacts.
    persisted_train = np.load(
        output_files["train"],
        mmap_mode="r",
        allow_pickle=False,
    )

    persisted_test = np.load(
        output_files["test"],
        mmap_mode="r",
        allow_pickle=False,
    )

    persisted_labels = np.load(
        output_files["labels"],
        mmap_mode="r",
        allow_pickle=False,
    )

    if persisted_train.shape != train_output.shape:
        raise AdvancedFeatureError("Persisted train shape mismatch")

    if persisted_test.shape != test_output.shape:
        raise AdvancedFeatureError("Persisted test shape mismatch")

    if not np.array_equal(persisted_labels, labels):
        raise AdvancedFeatureError("Persisted labels differ from baseline labels")

    for key, path in (
        ("train_features", output_files["train"]),
        ("test_features", output_files["test"]),
        ("test_labels", output_files["labels"]),
    ):
        if sha256_file(path) != manifest["files"][key]["sha256"]:
            raise AdvancedFeatureError(f"Output hash mismatch: {key}")

    return manifest