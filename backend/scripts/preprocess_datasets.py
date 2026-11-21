from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd


GRID_FACTOR_KG_PER_KWH = 0.710


def _read_household_power(input_path: Path) -> pd.DataFrame:
    if input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path) as archive:
            members = [name for name in archive.namelist() if name.endswith(".txt")]
            if len(members) != 1:
                raise ValueError("Expected one household power text file in the ZIP archive.")
            with archive.open(members[0]) as source:
                return pd.read_csv(
                    source,
                    sep=";",
                    na_values=["?"],
                    low_memory=False,
                )
    return pd.read_csv(input_path, sep=";", na_values=["?"], low_memory=False)


def preprocess(input_path: Path, output_path: Path) -> dict[str, int | str]:
    frame = _read_household_power(input_path)
    before = len(frame)
    frame = frame.drop_duplicates().dropna(how="all")
    required = {"Date", "Time", "Global_active_power"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    frame["timestamp"] = pd.to_datetime(
        frame["Date"].astype(str) + " " + frame["Time"].astype(str),
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    frame["Global_active_power"] = pd.to_numeric(
        frame["Global_active_power"], errors="coerce"
    )
    frame = frame.dropna(subset=["timestamp", "Global_active_power"])
    frame = frame[frame["Global_active_power"] >= 0]
    frame["period"] = frame["timestamp"].dt.strftime("%Y-%m")
    frame["activity_date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    daily = (
        frame.groupby(["period", "activity_date"], as_index=False)["Global_active_power"]
        .sum()
        .rename(columns={"Global_active_power": "quantity"})
    )
    daily["unit"] = "kWh"
    daily["category"] = "electricity"
    daily["description"] = "UCI household electricity consumption"
    daily["reporting_unit"] = "household"
    daily["factor_value"] = GRID_FACTOR_KG_PER_KWH
    daily["factor_year"] = 2024
    daily["emissions_kg"] = daily["quantity"] * daily["factor_value"]
    daily = daily[
        [
            "period",
            "activity_date",
            "category",
            "description",
            "quantity",
            "unit",
            "reporting_unit",
            "factor_value",
            "factor_year",
            "emissions_kg",
        ]
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_path, index=False)
    return {
        "rows_before": before,
        "rows_after": len(daily),
        "columns": len(daily.columns),
        "dataset_type": "household electricity aggregated daily",
    }


def preprocess_owid(input_path: Path, output_path: Path, country: str) -> dict[str, int | str]:
    frame = pd.read_csv(input_path, usecols=["country", "year", "iso_code", "co2", "co2_per_capita"])
    selected = frame[
        (frame["country"].str.casefold() == country.casefold())
        & frame["co2"].notna()
    ].copy()
    if selected.empty:
        raise ValueError(f"No OWID CO2 records found for country {country!r}.")
    # OWID's co2 column is million tonnes of CO2; convert to kg for the ledger.
    selected["period"] = selected["year"].astype(int).astype(str)
    selected["activity_date"] = selected["period"] + "-01-01"
    selected["category"] = "national_context"
    selected["description"] = f"OWID national CO2 context - {country}"
    selected["quantity"] = selected["co2"] * 1_000_000_000
    selected["unit"] = "kgCO2"
    selected["reporting_unit"] = country
    selected["factor_value"] = 1.0
    selected["factor_year"] = selected["year"].astype(int)
    selected["emissions_kg"] = selected["quantity"]
    result = selected[
        [
            "period",
            "activity_date",
            "category",
            "description",
            "quantity",
            "unit",
            "reporting_unit",
            "factor_value",
            "factor_year",
            "emissions_kg",
        ]
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {"rows_before": len(frame), "rows_after": len(result), "columns": len(result.columns), "dataset_type": "OWID annual national CO2 context"}


def preprocess_transport(input_path: Path, output_path: Path, entity: str) -> dict[str, int | str]:
    frame = pd.read_csv(
        input_path,
        usecols=["Entity", "Code", "Year", "Carbon dioxide emissions from transport"],
    )
    selected = frame[
        (frame["Entity"].str.casefold() == entity.casefold())
        & frame["Carbon dioxide emissions from transport"].notna()
    ].copy()
    if selected.empty:
        raise ValueError(f"No transport records found for entity {entity!r}.")
    selected["period"] = selected["Year"].astype(int).astype(str)
    selected["activity_date"] = selected["period"] + "-01-01"
    selected["category"] = "transport_context"
    selected["description"] = f"Annual transport CO2 emissions - {entity}"
    selected["quantity"] = pd.to_numeric(
        selected["Carbon dioxide emissions from transport"], errors="coerce"
    )
    selected["unit"] = "kgCO2"
    selected["reporting_unit"] = entity
    selected["factor_value"] = 1.0
    selected["factor_year"] = selected["Year"].astype(int)
    selected["emissions_kg"] = selected["quantity"]
    result = selected[
        [
            "period",
            "activity_date",
            "category",
            "description",
            "quantity",
            "unit",
            "reporting_unit",
            "factor_value",
            "factor_year",
            "emissions_kg",
        ]
    ].dropna(subset=["quantity"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {"rows_before": len(frame), "rows_after": len(result), "columns": len(result.columns), "dataset_type": "annual transport CO2 context"}


def preprocess_ev_charging(input_path: Path, output_path: Path) -> dict[str, int | str]:
    frame = pd.read_csv(input_path)
    required = {
        "Charging Start Time",
        "Energy Consumed (kWh)",
        "Vehicle Model",
        "Charging Station ID",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"EV charging dataset is missing columns: {', '.join(sorted(missing))}")
    frame["timestamp"] = pd.to_datetime(frame["Charging Start Time"], errors="coerce")
    frame["quantity"] = pd.to_numeric(frame["Energy Consumed (kWh)"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "quantity"])
    frame = frame[(frame["quantity"] >= 0) & (frame["quantity"] <= 500)]
    frame = frame.drop_duplicates()
    result = pd.DataFrame(
        {
            "period": frame["timestamp"].dt.strftime("%Y-%m"),
            "activity_date": frame["timestamp"].dt.strftime("%Y-%m-%d"),
            "category": "electricity",
            "description": "EV charging session - " + frame["Vehicle Model"].astype(str),
            "quantity": frame["quantity"],
            "unit": "kWh",
            "reporting_unit": frame["Charging Station ID"].astype(str),
            "factor_value": GRID_FACTOR_KG_PER_KWH,
            "factor_year": 2024,
        }
    )
    result["emissions_kg"] = result["quantity"] * result["factor_value"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "rows_before": len(frame),
        "rows_after": len(result),
        "columns": len(result.columns),
        "dataset_type": "user-provided EV charging sessions",
    }


def preprocess_urbanev(input_path: Path, output_path: Path) -> dict[str, int | str]:
    frame = pd.read_csv(input_path)
    if "time" not in frame.columns or len(frame.columns) < 2:
        raise ValueError("UrbanEV volume data requires a time column and zone columns.")
    frame["timestamp"] = pd.to_datetime(frame["time"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    zone_columns = [column for column in frame.columns if column not in {"time", "timestamp"}]
    long = frame.melt(
        id_vars=["timestamp"],
        value_vars=zone_columns,
        var_name="zone_id",
        value_name="quantity",
    )
    long["quantity"] = pd.to_numeric(long["quantity"], errors="coerce")
    long = long.dropna(subset=["quantity"])
    long = long[long["quantity"] >= 0]
    long["activity_date"] = long["timestamp"].dt.strftime("%Y-%m-%d")
    long["period"] = long["timestamp"].dt.strftime("%Y-%m")
    daily = (
        long.groupby(["period", "activity_date", "zone_id"], as_index=False)["quantity"]
        .sum()
    )
    daily["category"] = "electricity"
    daily["description"] = "UrbanEV zone charging volume"
    daily["unit"] = "kWh"
    daily["reporting_unit"] = "UrbanEV-zone-" + daily["zone_id"].astype(str)
    daily["factor_value"] = GRID_FACTOR_KG_PER_KWH
    daily["factor_year"] = 2024
    daily["emissions_kg"] = daily["quantity"] * daily["factor_value"]
    result = daily[
        [
            "period",
            "activity_date",
            "category",
            "description",
            "quantity",
            "unit",
            "reporting_unit",
            "factor_value",
            "factor_year",
            "emissions_kg",
        ]
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return {
        "rows_before": len(frame),
        "rows_after": len(result),
        "columns": len(result.columns),
        "dataset_type": "UrbanEV daily zone charging volume",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate and normalize a downloaded CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--kind",
        choices=("household", "owid", "transport", "ev_charging", "urbanev"),
        default="household",
    )
    parser.add_argument("--country", default="India", help="Country/entity filter for OWID or transport data.")
    args = parser.parse_args()
    if args.kind == "owid":
        print(preprocess_owid(args.input, args.output, args.country))
    elif args.kind == "transport":
        print(preprocess_transport(args.input, args.output, args.country))
    elif args.kind == "ev_charging":
        print(preprocess_ev_charging(args.input, args.output))
    elif args.kind == "urbanev":
        print(preprocess_urbanev(args.input, args.output))
    else:
        print(preprocess(args.input, args.output))
