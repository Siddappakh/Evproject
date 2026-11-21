# GreenTrack datasets

The repository does not commit downloaded third-party datasets or fabricated measurements.

The source catalog from `Actual_Dataset_Download_Links.xlsx` is preserved in
[dataset_catalog.json](./dataset_catalog.json). It records each dataset category,
source URL, access method, and link-verification status.

## Public sources

| Dataset | Source | Use | License/limitations |
|---|---|---|---|
| Our World in Data Energy | [owid-energy-data.csv](https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv) | Historical energy and emissions context | OWID grapher data; see the dataset's metadata and source-specific licenses |
| Caltech ACN-Data | [acnportal documentation](https://ev.caltech.edu/dataset) | EV charging-session research data | Access and terms are controlled by the ACN-Data service |
| India grid factors | [CEA CO2 Baseline Database](https://cea.nic.in/cdm-co2-baseline-database/) | India-specific electricity factors | Download the current official release and retain its version/date |

The verified direct OWID CSV and the user-provided household electricity, OWID
CO2, and transport CO2 files have been processed. ACN-Data is the next priority
because it provides genuine EV charging sessions. Portal-only sources are
documented but are not claimed as downloaded; see the catalog for limitations.

Run `python -m backend.scripts.download_datasets --output data/external` to download the
automated OWID source. Sources that require registration or manual download must not be
silently replaced with synthetic data.

Prepared data belongs in `data/processed/`. The ML training CSV must contain at least:
`period`, `activity_date`, `category`, `quantity`, `unit`, `reporting_unit`,
`factor_value`, `factor_year`, and `emissions_kg`.

## User-provided household electricity dataset

The UCI Individual Household Electric Power Consumption archive can be prepared
without copying the original 133 MB text file into the repository:

```powershell
python -m backend.scripts.preprocess_datasets `
  "C:\Users\Siddappa\Downloads\individual+household+electric+power+consumption.zip" `
  data\processed\household_power_activities.csv
```

The script handles the source's semicolon delimiter and `?` missing values,
removes invalid rows, aggregates minute readings to daily kWh, and calculates
electricity emissions using the configured 0.710 kgCO2e/kWh factor. This is
household electricity data, not EV charging-session data; combine it with
verified EV charging or transport records before claiming EV-specific model
performance.

## User-provided CO2 datasets

Prepare India-specific annual context records:

```powershell
python -m backend.scripts.preprocess_datasets `
  "C:\Users\Siddappa\Downloads\owid-co2-data.csv" `
  data\processed\owid_india_co2_context.csv `
  --kind owid --country India

python -m backend.scripts.preprocess_datasets `
  "C:\Users\Siddappa\Downloads\co2-emissions-transport.csv" `
  data\processed\transport_india_co2_context.csv `
  --kind transport --country India
```

These are annual national/context datasets, not individual EV charging sessions.
The OWID `co2` field is converted from million tonnes to kg; the transport file is
normalized to the platform's `emissions_kg` column. They are suitable for context
and annual trend analysis, but should not be merged with household daily records
without an explicit time-scale decision.

## User-provided EV charging archive

The archive `archive (5).zip` contains `ev_charging_patterns.csv`. Prepare its
normalized activity ledger with:

```powershell
Expand-Archive `
  "C:\Users\Siddappa\Downloads\archive (5).zip" `
  -DestinationPath data\external\ev_charging_patterns

python -m backend.scripts.preprocess_datasets `
  data\external\ev_charging_patterns\ev_charging_patterns.csv `
  data\processed\ev_charging_activities.csv `
  --kind ev_charging
```

The source contains EV session features such as energy consumed, charging
duration, vehicle model, charger type, battery state of charge, distance, and
station. The normalized file uses the India grid factor configured by the
platform for emissions estimation; this archive itself has no source/license
metadata, so it is recorded as user-provided and must not be presented as a
verified real-world benchmark without provenance confirmation.

## UrbanEV public charging dataset

UrbanEV is cloned to `data/external/UrbanEV/` from
[IntelligentSystemsLab/UrbanEV](https://github.com/IntelligentSystemsLab/UrbanEV).
The repository is CC0 licensed and documents public Shenzhen charging data from
September 2022 through February 2023. Convert its hourly zone charging volume
to daily normalized records with:

```powershell
python -m backend.scripts.preprocess_datasets `
  data\external\UrbanEV\data\volume.csv `
  data\processed\urbanev_zone_daily_activities.csv `
  --kind urbanev
```

The `volume.csv` values are charging volume in kWh derived from charging-pile
rated power, not direct vehicle-side meter readings. Use them for urban charging
demand forecasting and infrastructure analysis, and label them accordingly.
