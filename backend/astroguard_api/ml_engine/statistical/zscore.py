import numpy as np


class ZScoreDetector:
    def fit(self, x):
        self.mean_ = np.mean(x, axis=0)
        self.std_ = np.std(x, axis=0)
        self.std_[self.std_ < 1e-8] = 1.0
        return self

    def score(self, x):
        values = np.abs((x - self.mean_) / self.std_)
        return np.max(values, axis=1)

    def threshold(self, x, contamination=0.05):
        return float(
            np.quantile(self.score(x), 1.0 - contamination)
        )