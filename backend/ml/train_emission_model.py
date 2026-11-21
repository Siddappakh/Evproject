from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline

from .config import DATASET_VERSION, EMISSION_MODEL_PATH, METADATA_PATH
from .evaluation import regression_metrics
from .preprocessing import FEATURE_COLUMNS, records_to_frame, validate_training_frame, make_preprocessor


def train(records: list[dict[str, object]], output_path: Path = EMISSION_MODEL_PATH) -> dict[str, object]:
    frame = records_to_frame(records)
    validate_training_frame(frame, "emissions_kg")
    if len(frame) < 4:
        raise ValueError("At least four activity records are required for an emission model.")
    date_column = "activity_date" if "activity_date" in frame else "period"
    ordered_frame = frame.assign(
        _validation_date=pd.to_datetime(frame[date_column], errors="coerce")
    ).sort_values("_validation_date", na_position="last").drop(columns="_validation_date")
    split = max(1, int(len(ordered_frame) * 0.25))
    train_frame = ordered_frame.iloc[:-split]
    test_frame = ordered_frame.iloc[-split:]
    model = Pipeline(
        [
            ("preprocessor", make_preprocessor()),
            ("regressor", GradientBoostingRegressor(random_state=42, n_estimators=100)),
        ]
    )
    model.fit(train_frame[FEATURE_COLUMNS], train_frame["emissions_kg"])
    metrics = regression_metrics(
        test_frame["emissions_kg"], model.predict(test_frame[FEATURE_COLUMNS])
    )
    baseline = [float(train_frame["emissions_kg"].mean())] * len(test_frame)
    metrics["baseline_mae_kg"] = round(
        float(abs(test_frame["emissions_kg"] - baseline).mean()), 6
    )
    preprocessor = model.named_steps["preprocessor"]
    regressor = model.named_steps["regressor"]
    feature_names = preprocessor.get_feature_names_out()
    importance = sorted(
        (
            {"feature": str(name), "importance": round(float(value), 6)}
            for name, value in zip(feature_names, regressor.feature_importances_)
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )[:10]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)
    return {
        "metrics": metrics,
        "feature_importance": importance,
        "records": len(frame),
        "model": "GradientBoostingRegressor",
        "validation": "chronological 75/25 holdout",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the GreenTrack emission regressor.")
    parser.add_argument("csv", type=Path, help="Prepared CSV containing activity ledger columns.")
    args = parser.parse_args()
    result = train(pd.read_csv(args.csv).to_dict("records"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}
    metadata["emission"] = {
        **result,
        "dataset_version": DATASET_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
