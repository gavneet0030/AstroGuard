import json
import os
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict

from .config import ExperimentConfig
from .dataset import load_dataset

from .statistical.zscore import ZScoreDetector
from .statistical.robust_zscore import RobustZScoreDetector
from .statistical.rolling_detector import RollingRobustDetector

from .unsupervised.isolation_forest import IsolationForestDetector
from .supervised.random_forest import SupervisedAnomalyClassifier

from .evaluation.metrics import evaluate_model
from .registry.persistence import ModelRegistry


def run_experiments(root, output, config=None):
    root = Path(root).resolve()
    output = Path(output).resolve()

    config = config or ExperimentConfig()
    config.validate()

    output.mkdir(parents=True, exist_ok=True)

    registry = ModelRegistry(
        root / "artifacts" / "models" / "phase3"
    )

    report = {
        "phase": "3.0-3.5",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "channels": {},
        "policy": {
            "test_labels_used_for_training": False,
            "train_labels_required_for_supervised": True,
            "feature_source": "Existing Phase 2 processed matrices"
        }
    }

    for channel in ("a-1", "p-1"):
        print(f"\n[CHANNEL] {channel}", flush=True)

        bundle = load_dataset(
            root,
            channel,
            config.feature_set
        )

        x_train = bundle.x_train
        x_test = bundle.x_test
        y_test = bundle.y_test

        result = {
            "dataset": {
                "train_shape": list(x_train.shape),
                "test_shape": list(x_test.shape),
                "test_labels": len(y_test),
                "train_labels_available": bundle.y_train is not None,
                "fingerprint": bundle.fingerprint,
                "feature_count": x_train.shape[1]
            },
            "statistical": {}
        }

        # Z-score
        z_detector = ZScoreDetector().fit(x_train)
        z_scores = z_detector.score(x_test)
        z_threshold = z_detector.threshold(
            x_train,
            config.contamination
        )

        result["statistical"]["zscore"] = evaluate_model(
            y_test,
            z_scores,
            z_threshold
        )

        # Robust Z-score
        robust = RobustZScoreDetector().fit(x_train)
        robust_scores = robust.score(x_test)

        robust_threshold = max(
            config.robust_z_threshold,
            float(
                __import__("numpy").quantile(
                    robust.score(x_train),
                    1.0 - config.contamination
                )
            )
        )

        result["statistical"]["robust_zscore"] = evaluate_model(
            y_test,
            robust_scores,
            robust_threshold
        )

        # Causal rolling detector
        import numpy as np

        rolling = RollingRobustDetector(
            window=config.rolling_window
        )

        rolling_train = rolling.score(x_train[:, 0])
        rolling_test = rolling.score(x_test[:, 0])

        finite_rolling = rolling_train[
            np.isfinite(rolling_train)
        ]

        rolling_threshold = float(
            np.quantile(
                finite_rolling,
                1.0 - config.contamination
            )
        ) if finite_rolling.size else 3.5

        # A zero threshold can classify every test row as anomalous
        # when the training rolling-score distribution is dominated
        # by initial zero-history observations.
        if rolling_threshold <= 1e-8:
            positive_rolling = finite_rolling[
                finite_rolling > 1e-8
            ]

            if positive_rolling.size:
                rolling_threshold = float(
                    np.quantile(
                        positive_rolling,
                        1.0 - config.contamination
                    )
                )
            else:
                rolling_threshold = 3.5

        if not rolling_threshold > 0:
            rolling_threshold = 3.5

        result["statistical"]["rolling_robust"] = evaluate_model(
            y_test,
            rolling_test,
            rolling_threshold
        )

        # Isolation Forest
        detector = IsolationForestDetector(
            estimators=config.isolation_estimators,
            contamination=config.contamination,
            random_state=config.random_state,
            max_samples=config.max_samples
        ).fit(x_train)

        isolation_scores = detector.score(x_test)

        result["isolation_forest"] = evaluate_model(
            y_test,
            isolation_scores,
            detector.threshold_
        )

        artifact = registry.save(
            detector.model,
            channel,
            "isolation_forest",
            x_train.shape[1],
            bundle.feature_names,
            bundle.fingerprint,
            detector.threshold_,
            asdict(config)
        )

        result["isolation_forest"]["artifact_dir"] = str(artifact)

        # Supervised training
        supervised = SupervisedAnomalyClassifier(
            estimators=config.supervised_estimators,
            random_state=config.random_state
        )

        supervised_status = supervised.fit(
            x_train,
            bundle.y_train
        )

        if supervised_status["status"] == "TRAINED":
            supervised_scores = supervised.score(x_test)

            result["supervised"] = {
                "status": "TRAINED",
                "validation_f1": supervised_status["validation_f1"],
                "evaluation": evaluate_model(
                    y_test,
                    supervised_scores,
                    supervised.threshold_
                )
            }

            artifact = registry.save(
                supervised.model,
                channel,
                "random_forest",
                x_train.shape[1],
                bundle.feature_names,
                bundle.fingerprint,
                supervised.threshold_,
                asdict(config)
            )

            result["supervised"]["artifact_dir"] = str(artifact)

        else:
            result["supervised"] = supervised_status

        report["channels"][channel] = result

        del bundle, x_train, x_test, y_test

    report_path = output / "phase_3_report.json"
    temporary = output / "phase_3_report.json.tmp"

    temporary.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    os.replace(temporary, report_path)

    return report