import numpy as np


class RobustZScoreDetector:
    def fit(self, x):
        self.median_ = np.median(x, axis=0)

        mad = np.median(
            np.abs(x - self.median_),
            axis=0
        ) * 1.4826

        std = np.std(x, axis=0)

        self.scale_ = np.where(
            mad > 1e-8,
            mad,
            np.where(std > 1e-8, std, 1.0)
        )

        return self

    def score(self, x):
        values = np.abs((x - self.median_) / self.scale_)
        return np.max(values, axis=1)