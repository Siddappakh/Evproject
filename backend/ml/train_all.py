from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import DATASET_VERSION, METADATA_PATH
from .train_anomaly_model import train as train_anomaly
from .train_emission_model import train as train_emission
from .train_forecasting_model import train as train_forecast


def main() -> None:
    parser = argparse.ArgumentParser(description="Train all GreenTrack ML artifacts from one prepared CSV.")
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    records = pd.read_csv(args.csv).to_dict("records")
    results = {
        "anomaly": train_anomaly(records),
        "emission": train_emission(records),
        "forecast": train_forecast(records),
    }
    metadata = {
        name: {
            **result,
            "dataset_version": DATASET_VERSION,
            "dataset_path": str(args.csv),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        for name, result in results.items()
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
