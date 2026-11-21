from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import Ridge

from .config import DATASET_VERSION, FORECAST_MODEL_PATH, METADATA_PATH
from .evaluation import regression_metrics


def train(records: list[dict[str, object]], output_path: Path = FORECAST_MODEL_PATH) -> dict[str, object]:
    frame = pd.DataFrame(records)
    if frame.empty or "period" not in frame or "emissions_kg" not in frame:
        raise ValueError("Forecast training data requires period and emissions_kg columns.")
    monthly = (
        frame.assign(emissions_kg=pd.to_numeric(frame["emissions_kg"], errors="coerce"))
        .dropna(subset=["emissions_kg"])
        .groupby("period", as_index=False)["emissions_kg"]
        .sum()
        .sort_values("period")
    )
    if len(monthly) < 4:
        raise ValueError("At least four monthly periods are required for forecasting.")
    monthly["period"] = pd.PeriodIndex(monthly["period"], freq="M")
    all_periods = pd.period_range(monthly["period"].min(), monthly["period"].max(), freq="M")
    observed = monthly.set_index("period")["emissions_kg"]
    observed_indices = [all_periods.get_loc(period) for period in observed.index]

    holdout_count = max(1, int(len(observed) * 0.2))
    train_values = observed.iloc[:-holdout_count]
    test_values = observed.iloc[-holdout_count:]
    train_indices = [all_periods.get_loc(period) for period in train_values.index]
    validation_model = Ridge(alpha=1.0)
    validation_model.fit([[index] for index in train_indices], train_values.values)
    validation_metrics = regression_metrics(
        test_values.values,
        validation_model.predict(
            [[all_periods.get_loc(period)] for period in test_values.index]
        ),
    )

    model = Ridge(alpha=1.0)
    model.fit([[index] for index in observed_indices], observed.values)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "periods": [str(period) for period in all_periods]}, output_path)
    return {
        "records": len(frame),
        "periods": len(monthly),
        "model": "Ridge time trend",
        "validation": "chronological last-period backtest",
        "validation_metrics": validation_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the GreenTrack time trend model.")
    parser.add_argument("csv", type=Path, help="Prepared CSV containing period and emissions_kg.")
    args = parser.parse_args()
    result = train(pd.read_csv(args.csv).to_dict("records"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}
    metadata["forecast"] = {
        **result,
        "dataset_version": DATASET_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
