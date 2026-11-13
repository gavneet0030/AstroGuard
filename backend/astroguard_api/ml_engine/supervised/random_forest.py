import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score


class SupervisedAnomalyClassifier:
    def __init__(self, estimators=100, random_state=42):
        self.estimators = estimators
        self.random_state = random_state

    def fit(self, x, y):
        if y is None:
            return {
                "status": "SKIPPED",
                "reason": "train_labels.npy is absent."
            }

        y = np.asarray(y)

        if len(y) != len(x):
            raise ValueError("Training labels are not aligned.")

        if len(np.unique(y)) != 2:
            return {
                "status": "SKIPPED",
                "reason": "Training labels require both classes."
            }

        if np.min(np.bincount(y.astype(int), minlength=2)) < 2:
            return {
                "status": "SKIPPED",
                "reason": "Insufficient examples for stratified validation."
            }

        x_train, x_valid, y_train, y_valid = train_test_split(
            x,
            y,
            test_size=0.2,
            random_state=self.random_state,
            stratify=y
        )

        self.model = RandomForestClassifier(
            n_estimators=self.estimators,
            class_weight="balanced_subsample",
            random_state=self.random_state,
            n_jobs=1,
            min_samples_leaf=2
        )

        self.model.fit(x_train, y_train)

        probabilities = self.model.predict_proba(x_valid)[:, 1]

        best_f1 = -1.0
        best_threshold = 0.5

        for threshold in np.linspace(0.1, 0.9, 17):
            predictions = (probabilities >= threshold).astype(int)

            score = f1_score(
                y_valid,
                predictions,
                zero_division=0
            )

            if score > best_f1:
                best_f1 = float(score)
                best_threshold = float(threshold)

        self.threshold_ = best_threshold

        return {
            "status": "TRAINED",
            "validation_f1": best_f1,
            "threshold": self.threshold_
        }

    def score(self, x):
        return self.model.predict_proba(x)[:, 1]

    def predict(self, x):
        return (
            self.score(x) >= self.threshold_
        ).astype(np.int8)