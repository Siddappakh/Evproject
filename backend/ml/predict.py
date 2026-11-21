from __future__ import annotations

from typing import Iterable

import pandas as pd

from .model_loader import load_anomaly_model, load_emission_model, load_forecast_model, load_urbanev_demand_model
from .preprocessing import records_to_frame


def predict_emissions(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    frame = records_to_frame(records)
    if frame.empty:
        return []
    model = load_emission_model()
    values = model.predict(frame)
    return [
        {
            "predicted_emissions_kg": round(max(0.0, float(value)), 6),
            "unit": "kgCO2e",
            "model": "GradientBoostingRegressor",
            "estimated": True,
        }
        for value in values
    ]


def detect_anomalies(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    source = list(records)
    frame = records_to_frame(source)
    if frame.empty:
        return []
    model = load_anomaly_model()
    scores = model.decision_function(frame)
    labels = model.predict(frame)
    results = []
    for row, score, label in zip(source, scores, labels):
        results.append(
            {
                "record_id": row.get("id"),
                "date": row.get("activity_date") or row.get("period"),
                "category": row.get("category"),
                "anomaly_score": round(float(score), 6),
                "is_anomaly": bool(label == -1),
                "observed_emissions_kg": float(row.get("emissions_kg", 0) or 0),
                "explanation": (
                    "Isolation Forest flagged this record as unusual among the supplied activity features."
                    if label == -1
                    else "No unusual pattern was detected among the supplied activity features."
                ),
                "limitations": "The anomaly score is not a causal explanation.",
            }
        )
    return results


def forecast_emissions(records: Iterable[dict[str, object]], periods: int = 6) -> list[dict[str, object]]:
    artifact = load_forecast_model()
    model = artifact["model"]
    known_periods = artifact["periods"]
    if not known_periods:
        raise ValueError("Forecast model has no training periods.")
    last_period = pd.Period(str(known_periods[-1]), freq="M")
    values = model.predict([[len(known_periods) + offset] for offset in range(periods)])
    return [
        {
            "period": str(last_period + offset + 1),
            "predicted_emissions_kg": round(max(0.0, float(value)), 6),
            "unit": "kgCO2e",
            "model": "Ridge time trend",
            "estimated": True,
        }
        for offset, value in enumerate(values)
    ]


def predict_urbanev_demand(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    source = list(records)
    if not source:
        return []
    artifact = load_urbanev_demand_model()
    frame = pd.DataFrame(source)
    timestamps = pd.to_datetime(frame["recorded_at"], errors="coerce")
    frame["hour"] = timestamps.dt.hour
    frame["day_of_week"] = timestamps.dt.dayofweek
    frame["month"] = timestamps.dt.month
    frame["zone_code"] = frame["zone_id"].map(artifact["zone_values"]).fillna(-1)
    values = artifact["model"].predict(frame[artifact["features"]])
    return [
        {
            "recorded_at": row.get("recorded_at"),
            "zone_id": row.get("zone_id"),
            "actual_kwh": row.get("charging_volume_kwh"),
            "predicted_kwh": round(max(0.0, float(value)), 6),
            "estimated": True,
        }
        for row, value in zip(source, values)
    ]
