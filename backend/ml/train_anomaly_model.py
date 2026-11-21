from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline

from .config import ANOMALY_MODEL_PATH, DATASET_VERSION, METADATA_PATH
from .preprocessing import FEATURE_COLUMNS, make_preprocessor, records_to_frame, validate_training_frame


def train(records: list[dict[str, object]], output_path: Path = ANOMALY_MODEL_PATH) -> dict[str, object]:
    frame = records_to_frame(records)
    validate_training_frame(frame)
    if len(frame) < 10:
        raise ValueError("At least ten activity records are required for anomaly detection.")
    model = Pipeline(
        [
            ("preprocessor", make_preprocessor()),
            ("detector", IsolationForest(contamination="auto", random_state=42, n_estimators=200)),
        ]
    )
    model.fit(frame[FEATURE_COLUMNS])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)
    return {"records": len(frame), "model": "IsolationForest", "contamination": "auto"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the GreenTrack anomaly detector.")
    parser.add_argument("csv", type=Path, help="Prepared CSV containing activity ledger columns.")
    args = parser.parse_args()
    result = train(pd.read_csv(args.csv).to_dict("records"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}
    metadata["anomaly"] = {
        **result,
        "dataset_version": DATASET_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

