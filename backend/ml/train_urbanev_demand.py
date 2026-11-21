from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from backend.app import database

from .config import MODEL_DIR

FEATURES = [
    "zone_id", "hour", "day_of_week", "month", "occupancy",
    "duration_hours", "electricity_price", "service_price", "temperature",
]
NUMERIC = [feature for feature in FEATURES if feature != "zone_id"]
MODEL_PATH = MODEL_DIR / "urbanev_demand_model.joblib"
METADATA_PATH = MODEL_DIR / "urbanev_demand_metadata.json"


def load_urbanev(data_dir: Path) -> pd.DataFrame:
    def wide(name: str) -> pd.DataFrame:
        frame = pd.read_csv(data_dir / name)
        frame["timestamp"] = pd.to_datetime(frame.pop("time"), errors="coerce")
        return frame.set_index("timestamp").stack().rename(name[:-4])

    joined = pd.concat(
        [wide(name) for name in ("volume.csv", "duration.csv", "occupancy.csv", "e_price.csv", "s_price.csv")],
        axis=1,
        join="inner",
    ).reset_index().rename(columns={"level_1": "zone_id"})
    weather = pd.read_csv(data_dir / "weather_central.csv")
    weather["timestamp"] = pd.to_datetime(weather.pop("time"), errors="coerce")
    temperature = weather[["timestamp", "T"]].rename(columns={"T": "temperature"})
    result = joined.merge(temperature, on="timestamp", how="left")
    result = result.rename(columns={"volume": "target", "duration": "duration_hours",
                                    "occupancy": "occupancy", "e_price": "electricity_price",
                                    "s_price": "service_price"})
    result["hour"] = result["timestamp"].dt.hour
    result["day_of_week"] = result["timestamp"].dt.dayofweek
    result["month"] = result["timestamp"].dt.month
    return result.dropna(subset=["timestamp", "zone_id", "target"])


def train(data_dir: Path, output_path: Path = MODEL_PATH) -> dict[str, object]:
    frame = load_urbanev(data_dir).sort_values("timestamp")
    if len(frame) < 100:
        raise ValueError("UrbanEV demand data is too small to train.")
    split = int(len(frame) * 0.8)
    train_frame, test_frame = frame.iloc[:split].copy(), frame.iloc[split:].copy()
    zone_values = {zone: index for index, zone in enumerate(sorted(frame["zone_id"].unique()))}
    for current in (train_frame, test_frame):
        current["zone_code"] = current["zone_id"].map(zone_values).fillna(-1)
    model_features = ["zone_code"] + NUMERIC
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    preprocessor = ColumnTransformer([("numeric", numeric, model_features)])
    model = Pipeline([("preprocessor", preprocessor),
                      ("regressor", HistGradientBoostingRegressor(
                          random_state=42, max_iter=150, max_leaf_nodes=31
                      ))])
    model.fit(train_frame[model_features], train_frame["target"])
    predicted = np.maximum(0, model.predict(test_frame[model_features]))
    actual = test_frame["target"].to_numpy()
    nonzero = actual != 0
    metrics = {
        "mae_kwh": round(float(mean_absolute_error(actual, predicted)), 6),
        "rmse_kwh": round(float(np.sqrt(mean_squared_error(actual, predicted))), 6),
        "mape_percent": round(float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100), 6) if nonzero.any() else None,
        "r2": round(float(r2_score(actual, predicted)), 6),
        "baseline_mae_kwh": round(float(mean_absolute_error(actual, [train_frame["target"].mean()] * len(actual))), 6),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model, "features": model_features, "zone_values": zone_values,
        "last_timestamp": frame["timestamp"].max().isoformat(),
    }, output_path)
    metadata = {
        "model": "UrbanEV charging demand HistGradientBoostingRegressor",
        "model_version": "urbanev-demand-v1",
        "dataset": "UrbanEV",
        "dataset_version": "44f2aa0c8d89f192bce00bafb0def74a21b39c68",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_start": train_frame["timestamp"].min().isoformat(),
        "training_end": train_frame["timestamp"].max().isoformat(),
        "testing_start": test_frame["timestamp"].min().isoformat(),
        "testing_end": test_frame["timestamp"].max().isoformat(),
        "features": model_features,
        "target": "zone-hour charging volume (kWh)",
        "metrics": metrics,
        "artifact_path": str(output_path),
        "status": "success",
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    database.initialize_database()
    database.save_ml_model_run({
        "model_name": metadata["model"],
        "model_version": metadata["model_version"],
        "dataset_name": metadata["dataset"],
        "dataset_version": metadata["dataset_version"],
        "trained_at": metadata["trained_at"],
        "training_start": metadata["training_start"],
        "training_end": metadata["training_end"],
        "testing_start": metadata["testing_start"],
        "testing_end": metadata["testing_end"],
        "features": metadata["features"],
        "target": metadata["target"],
        "metrics": metadata["metrics"],
        "artifact_path": metadata["artifact_path"],
        "status": metadata["status"],
    })
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(train(args.data_dir), indent=2))
