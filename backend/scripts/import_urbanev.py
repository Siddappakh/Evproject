from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backend.app import database


VERSION = "44f2aa0c8d89f192bce00bafb0def74a21b39c68"


def load(data_dir: Path) -> list[dict[str, object]]:
    def read(name: str) -> pd.DataFrame:
        frame = pd.read_csv(data_dir / name)
        frame["recorded_at"] = pd.to_datetime(frame.pop("time"), errors="coerce")
        return frame.set_index("recorded_at").stack().rename(name[:-4])

    joined = pd.concat(
        [read(name) for name in ("volume.csv", "duration.csv", "occupancy.csv", "e_price.csv", "s_price.csv")],
        axis=1,
        join="inner",
    ).reset_index().rename(columns={"level_1": "zone_id"})
    weather = pd.read_csv(data_dir / "weather_central.csv")
    weather["recorded_at"] = pd.to_datetime(weather.pop("time"), errors="coerce")
    joined = joined.merge(weather[["recorded_at", "T"]], on="recorded_at", how="left")
    joined = joined.rename(columns={"volume": "charging_volume_kwh", "duration": "duration_hours",
                                    "e_price": "electricity_price", "s_price": "service_price",
                                    "T": "temperature"})
    joined = joined.dropna(subset=["recorded_at", "charging_volume_kwh", "zone_id"])
    return joined.to_dict("records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import UrbanEV hourly records into SQLite.")
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    database.initialize_database()
    records = load(args.data_dir)
    imported = database.import_urbanev_records(records, VERSION)
    print({"read": len(records), "imported": imported, "dataset_version": VERSION})
