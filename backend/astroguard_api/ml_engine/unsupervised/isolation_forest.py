import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    def __init__(
        self,
        estimators=100,
        contamination=0.05,
        random_state=42,
        max_samples=2048
    ):
        self.estimators = estimators
        self.contamination = contamination
        self.random_state = random_state
        self.max_samples = max_samples

    def fit(self, x):
        self.model = IsolationForest(
            n_estimators=self.estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            max_samples=min(self.max_samples, len(x)),
            n_jobs=1
        )

        self.model.fit(x)

        train_scores = -self.model.score_samples(x)

        self.threshold_ = float(
            np.quantile(
                train_scores,
                1.0 - self.contamination
            )
        )

        return self

    def score(self, x):
        return -self.model.score_samples(x)

    def predict(self, x):
        return (self.score(x) >= self.threshold_).astype(np.int8)