from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentConfig:
    random_state: int = 42
    contamination: float = 0.05
    robust_z_threshold: float = 3.5
    rolling_window: int = 30
    isolation_estimators: int = 100
    supervised_estimators: int = 100
    max_samples: int = 2048
    feature_set: str = "advanced"

    def validate(self):
        if not 0.001 <= self.contamination <= 0.5:
            raise ValueError("Invalid contamination.")

        if self.rolling_window < 2:
            raise ValueError("Rolling window must be >= 2.")

        if self.feature_set not in ("advanced", "baseline"):
            raise ValueError("Invalid feature set.")