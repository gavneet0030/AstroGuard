import numpy as np

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix
)


def evaluate_model(y_true, scores, threshold):
    y_true = np.asarray(y_true, dtype=np.int8)
    scores = np.asarray(scores, dtype=np.float64)

    if len(y_true) != len(scores):
        raise ValueError("Evaluation arrays are not aligned.")

    if not np.isfinite(scores).all():
        raise ValueError("Scores contain non-finite values.")

    predictions = (scores >= threshold).astype(np.int8)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1]
    ).ravel()

    normal_count = int(tn + fp)
    anomaly_count = int(tp + fn)

    return {
        "precision": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, predictions, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, predictions, zero_division=0)
        ),
        "pr_auc_average_precision": (
            float(average_precision_score(y_true, scores))
            if anomaly_count else None
        ),
        "roc_auc": (
            float(roc_auc_score(y_true, scores))
            if len(np.unique(y_true)) == 2 else None
        ),
        "false_alarm_rate": (
            float(fp / normal_count)
            if normal_count else 0.0
        ),
        "specificity": (
            float(tn / normal_count)
            if normal_count else 0.0
        ),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp)
        },
        "threshold": float(threshold)
    }