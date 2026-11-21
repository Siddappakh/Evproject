from __future__ import annotations

from typing import Iterable

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_FEATURES = [
    "quantity",
    "factor_value",
    "factor_year",
    "month",
    "day_of_month",
    "day_of_week",
]
CATEGORICAL_FEATURES = ["category", "unit", "reporting_unit"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def records_to_frame(records: Iterable[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(records))
    if frame.empty:
        return frame
    for column in ("quantity", "factor_value", "factor_year", "emissions_kg"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    dates = pd.to_datetime(
        frame.get("activity_date", frame.get("period")),
        errors="coerce",
        format="mixed",
    )
    frame["month"] = dates.dt.month
    frame["day_of_month"] = dates.dt.day
    frame["day_of_week"] = dates.dt.dayofweek
    for column in CATEGORICAL_FEATURES:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    return frame


def validate_training_frame(frame: pd.DataFrame, target: str | None = None) -> None:
    if frame.empty:
        raise ValueError("Training data is empty.")
    required = set(FEATURE_COLUMNS)
    if target:
        required.add(target)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Training data is missing columns: {', '.join(missing)}")
    if frame[NUMERIC_FEATURES].isna().all(axis=None):
        raise ValueError("Training data has no usable numeric features.")
    if target and frame[target].isna().any():
        raise ValueError(f"Training target {target!r} contains missing values.")


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )

