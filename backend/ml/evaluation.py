from __future__ import annotations

from typing import Iterable

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(actual: Iterable[float], predicted: Iterable[float]) -> dict[str, float]:
    y_true = np.asarray(list(actual), dtype=float)
    y_pred = np.asarray(list(predicted), dtype=float)
    if len(y_true) == 0:
        raise ValueError("Cannot evaluate an empty test set.")
    return {
        "mae_kg": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "rmse_kg": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 6),
        "r2": round(float(r2_score(y_true, y_pred)), 6) if len(y_true) > 1 else 0.0,
    }

