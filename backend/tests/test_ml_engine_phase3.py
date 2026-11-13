import numpy as np
import pytest

from astroguard_api.ml_engine.config import ExperimentConfig
from astroguard_api.ml_engine.contracts import DatasetBundle

from astroguard_api.ml_engine.statistical.zscore import ZScoreDetector
from astroguard_api.ml_engine.statistical.robust_zscore import RobustZScoreDetector
from astroguard_api.ml_engine.statistical.rolling_detector import RollingRobustDetector

from astroguard_api.ml_engine.evaluation.metrics import evaluate_model


def test_config_validation():
    ExperimentConfig().validate()

    with pytest.raises(ValueError):
        ExperimentConfig(contamination=0.9).validate()


def test_zscore_detector():
    x = np.arange(100, dtype=np.float32).reshape(50, 2)

    detector = ZScoreDetector().fit(x)

    scores = detector.score(x)

    assert scores.shape == (50,)
    assert np.isfinite(scores).all()


def test_robust_zscore_detector():
    x = np.arange(100, dtype=np.float32).reshape(50, 2)

    detector = RobustZScoreDetector().fit(x)

    scores = detector.score(x)

    assert len(scores) == 50
    assert np.isfinite(scores).all()


def test_rolling_detector():
    values = np.arange(100, dtype=np.float32)

    detector = RollingRobustDetector(window=10)

    scores = detector.score(values)

    assert len(scores) == len(values)
    assert scores[0] == 0
    assert np.isfinite(scores).all()


def test_metrics():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.8, 0.9, 0.2])

    result = evaluate_model(y, scores, 0.5)

    assert result["confusion_matrix"]["tn"] == 1
    assert result["confusion_matrix"]["fp"] == 1
    assert result["confusion_matrix"]["fn"] == 1
    assert result["confusion_matrix"]["tp"] == 1

    assert result["false_alarm_rate"] == 0.5


def test_dataset_contract_rejects_nonfinite():
    bundle = DatasetBundle(
        channel="a-1",
        x_train=np.array([[1, np.nan]], dtype=np.float32),
        x_test=np.array([[1, 2]], dtype=np.float32),
        y_test=np.array([0]),
        y_train=None,
        train_path=None,
        test_path=None,
        labels_path=None,
        feature_names=["f0", "f1"],
        fingerprint="test"
    )

    with pytest.raises(ValueError):
        bundle.validate()