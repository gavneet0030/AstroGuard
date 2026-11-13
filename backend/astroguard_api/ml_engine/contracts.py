from dataclasses import dataclass
from pathlib import Path
import numpy as np


@dataclass
class DatasetBundle:
    channel: str
    x_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    y_train: object
    train_path: Path
    test_path: Path
    labels_path: Path
    feature_names: list
    fingerprint: str

    def validate(self):
        if self.channel not in ("a-1", "p-1"):
            raise ValueError("Unsupported channel.")

        if self.x_train.ndim != 2 or self.x_test.ndim != 2:
            raise ValueError("Feature arrays must be two-dimensional.")

        if self.x_train.shape[1] != self.x_test.shape[1]:
            raise ValueError("Train/test feature dimensions differ.")

        if not np.isfinite(self.x_train).all():
            raise ValueError("Training data contains non-finite values.")

        if not np.isfinite(self.x_test).all():
            raise ValueError("Test data contains non-finite values.")

        if self.y_test.ndim != 1:
            raise ValueError("Labels must be one-dimensional.")

        if len(self.y_test) != len(self.x_test):
            raise ValueError("Test labels are not row-aligned.")

        if not np.isin(self.y_test, [0, 1]).all():
            raise ValueError("Labels must be binary.")

        if self.y_train is not None:
            if len(self.y_train) != len(self.x_train):
                raise ValueError("Training labels are not row-aligned.")

            if not np.isin(self.y_train, [0, 1]).all():
                raise ValueError("Training labels must be binary.")

        if len(self.feature_names) != self.x_train.shape[1]:
            raise ValueError("Feature-name count mismatch.")