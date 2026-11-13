import numpy as np

from ..registry.persistence import ModelRegistry


class InferenceService:
    def __init__(self, registry_root):
        self.registry = ModelRegistry(registry_root)

    def predict(self, channel, model_name, features):
        model, manifest = self.registry.load(
            channel,
            model_name
        )

        matrix = np.asarray(features, dtype=np.float32)

        if matrix.ndim != 2:
            raise ValueError("Input must be a two-dimensional matrix.")

        if matrix.shape[1] != manifest["feature_count"]:
            raise ValueError("Incorrect feature count.")

        if not np.isfinite(matrix).all():
            raise ValueError("Input contains non-finite values.")

        if model_name == "isolation_forest":
            scores = -model.score_samples(matrix)
        else:
            scores = model.predict_proba(matrix)[:, 1]

        threshold = float(manifest["threshold"])

        predictions = (
            scores >= threshold
        ).astype(int)

        return {
            "channel": channel,
            "model": model_name,
            "threshold": threshold,
            "predictions": predictions.tolist(),
            "scores": scores.astype(float).tolist()
        }