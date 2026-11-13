import numpy as np


class RollingRobustDetector:
    def __init__(self, window=30, min_periods=5):
        self.window = window
        self.min_periods = min_periods

    def score(self, values):
        values = np.asarray(values, dtype=np.float64)

        if values.ndim != 1:
            raise ValueError("Rolling detector expects one-dimensional data.")

        result = np.zeros(len(values), dtype=np.float32)
        history = []

        for index, value in enumerate(values):
            if len(history) >= self.min_periods:
                reference = np.asarray(
                    history[-self.window:],
                    dtype=np.float64
                )

                median = np.median(reference)

                mad = (
                    np.median(np.abs(reference - median)) * 1.4826
                )

                scale = mad

                if scale <= 1e-8:
                    scale = max(float(np.std(reference)), 1.0)

                result[index] = abs(float(value) - median) / scale

            history.append(float(value))

        return result