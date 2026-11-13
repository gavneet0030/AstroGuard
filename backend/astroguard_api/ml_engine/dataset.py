from pathlib import Path
import numpy as np

from .contracts import DatasetBundle
from .fingerprints import dataset_fingerprint


CHANNELS = ("a-1", "p-1")


def load_dataset(root, channel, feature_set="advanced"):
    root = Path(root)

    if channel not in CHANNELS:
        raise ValueError("Unsupported channel.")

    if feature_set == "advanced":
        folder = (
            root / "data" / "processed" /
            "advanced_telemetry_features" / "smap" / channel
        )
        train_name = "train_features_advanced.npy"

    elif feature_set == "baseline":
        folder = (
            root / "data" / "processed" /
            "telemetry_features" / "smap" / channel
        )
        train_name = "train_features.npy"

    else:
        raise ValueError("Invalid feature set.")

    train_path = folder / train_name
    test_path = folder / (
        "test_features_advanced.npy"
        if feature_set == "advanced"
        else "test_features.npy"
    )
    labels_path = folder / "test_labels.npy"

    for path in (train_path, test_path, labels_path):
        if not path.is_file():
            raise FileNotFoundError(str(path))

    x_train = np.asarray(
        np.load(train_path, mmap_mode="r", allow_pickle=False),
        dtype=np.float32
    )

    x_test = np.asarray(
        np.load(test_path, mmap_mode="r", allow_pickle=False),
        dtype=np.float32
    )

    y_test = np.asarray(
        np.load(labels_path, mmap_mode="r", allow_pickle=False),
        dtype=np.int8
    )

    train_labels_path = folder / "train_labels.npy"

    y_train = None

    if train_labels_path.is_file():
        y_train = np.asarray(
            np.load(train_labels_path, mmap_mode="r", allow_pickle=False),
            dtype=np.int8
        )

    feature_names = [
        f"feature_{index:03d}"
        for index in range(x_train.shape[1])
    ]

    paths = [train_path, test_path, labels_path]

    if y_train is not None:
        paths.append(train_labels_path)

    bundle = DatasetBundle(
        channel=channel,
        x_train=x_train,
        x_test=x_test,
        y_test=y_test,
        y_train=y_train,
        train_path=train_path,
        test_path=test_path,
        labels_path=labels_path,
        feature_names=feature_names,
        fingerprint=dataset_fingerprint(paths)
    )

    bundle.validate()
    return bundle