# Emission Factor Audit

**Project:** GreenTrack / EV Carbon Footprint and Reduction  
**Audit date:** 2026-11-17  
**Scope:** Existing source code, SQLite seed data, API paths, frontend calculation surfaces, reports, and tests  
**Change policy:** This audit did not change application behavior, factor values, database records, or user activities.

## Executive summary

The application has one central reference registry in
`backend/app/carbon.py`. `POST /api/factors/seed` copies those records into
the workspace's `emission_factors` table through
`backend/app/database.py`. Activities store a snapshot of the selected factor,
including value, unit, source, year, region, and assumptions.

The current reference registry contains **16 definitions**:

- 2 electricity factors (FY 2024-25 and FY 2025-26)
- 6 transport factors
- 4 fuel factors
- 3 waste factors
- 1 water factor

The deterministic calculation engine is structurally sound for factors whose
denominator matches the activity unit. The audit found, however, that most
factor provenance is not sufficient to classify the values as official,
versioned, region-appropriate factors. Several source URLs are landing pages
rather than the original table, workbook, or methodology used to obtain the
number.

There are also **non-registry constants** that materially affect results:
the event calculator uses 0.71 kg/kWh, 1.5 kg/person for meals, and 0.089
kg/person-km for travel; campus food waste uses 0.625 kg/kg; GPS trips default
to 0.170 kg/km; and impact equivalents use 22 kg/tree/year. These values must
be audited separately from the database registry.

## Migrated database status

The November 17, 2026 migration reclassified all six database records named
`Municipal Water Supply` from `waste` to `water` in place. Factor IDs and
workspace associations were preserved. Existing activity rows and their
historical category, factor snapshot, and calculated emissions were not
rewritten; their foreign-key links remain valid. New water activities use the
`water` category.

The preserved legacy factor named `CEA National Grid Electricity Baseline`
remains in its original workspace with its original `CO2e` gas basis and
unverified classification. It is excluded from automatic and explicit
selection for new electricity calculations. The fiscal-year-specific CEA
factors are the selectable records for their effective periods.

No additional source publication/version or verification date was added for
the 85 unverified records. Their source names and URLs remain documented
without upgrading their classifications, because the exact source
publication, value, unit, region, and methodology could not be established
from the existing evidence.

## Classification meanings

- **Official:** The exact value, unit, boundary, geography, and version can be
  tied to an authoritative original publication.
- **Estimated:** A plausible value or transparent derivation exists, but one or
  more required provenance or applicability details are missing.
- **Demonstration:** A product/demo assumption used to make a feature work,
  not suitable as a verified inventory factor.
- **Unverified:** A value is present, but the cited source does not establish
  the exact value and applicability from the information stored in the app.

## Inventory: factors in `REFERENCE_FACTORS`

The following values are defined in `backend/app/carbon.py` and inserted by
`database.seed_reference_factors_if_empty()` for each workspace. The registry
contains 16 definitions; the database stores a workspace-specific copy of each
definition.

The migrated database snapshot contains **97 records** across **6 workspaces**:
96 current reference records (16 definitions x 6 workspaces) and one preserved
legacy electricity record. The legacy record is retained for historical
references, is classified as unverified, and is excluded from new electricity
factor selection.

| Factor name | Category | Value | Unit | Region | Year | Existing source | Publication/version evidence | Classification | Used by |
|---|---:|---:|---|---|---:|---|---|---|---|
| CEA National Grid Electricity Baseline | electricity | 0.710 | kgCO2e/kWh | India | 2024 | Central Electricity Authority (CEA), Ministry of Power | Cites the CEA CDM page but stores no database version, workbook, table, or fiscal-year mapping. CEA Version 22.0 reports 0.675 tCO2/MWh for FY 2025–26; the project value is therefore not the current CEA value. | **Unverified** | Seeded electricity factor; manual activities; OCR electricity bills; event generator calculation; ML preprocessing constant. |
| Passenger Car (Petrol / Gasoline) | transport | 0.170 | kgCO2e/km | Global Average | 2024 | UK DEFRA / GHG Protocol | Generic 2024 DEFRA collection URL; no workbook sheet, vehicle class, fuel basis, or exact row is recorded. | **Unverified** | Seeded transport factor; GPS default and car mode; README table. |
| Motorcycle / Two-Wheeler (Petrol) | transport | 0.045 | kgCO2e/km | India / Global | 2024 | ARAI & DEFRA | Generic ARAI home page plus generic DEFRA collection; no exact publication, vehicle class, test cycle, or row is recorded. | **Unverified** | Seeded transport factor; GPS motorcycle mode. |
| Electric Vehicle (Grid Charged EV) | transport | 0.053 | kgCO2e/km | India | 2024 | BEE & CEA India Grid | The assumptions disclose a derivation: 0.71 kg/kWh × 0.075 kWh/km = 0.05325 kg/km, rounded to 0.053. The efficiency source and CEA version are not recorded. | **Estimated** | Seeded transport factor; available for manual activities. |
| Public Transit Bus (Per Passenger) | transport | 0.089 | kgCO2e/km | Global Average | 2024 | UK DEFRA | Generic collection URL; no exact bus mode, occupancy, life-cycle boundary, or workbook row is recorded. | **Unverified** | Seeded factor; GPS bus mode; event travel calculation. |
| Metro Rail / Suburban Electric Train | transport | 0.035 | kgCO2e/km | India | 2024 | DMRC / DEFRA | Generic DMRC home page and DEFRA collection; no DMRC inventory or exact DEFRA row/version is recorded. | **Unverified** | Seeded factor; manual activities. |
| Walking / Bicycling (Active Travel) | transport | 0.000 | kgCO2e/km | Global | 2024 | GHG Protocol Corporate Standard | The cited standard is not an exact source for a zero life-cycle factor. The value means zero direct tailpipe emissions only. | **Estimated** | Seeded factor; GPS walking and bicycle modes. |
| Motor Gasoline / Petrol Fuel | fuel | 2.310 | kgCO2e/L | Global | 2024 | US EPA GHG Emission Factors Hub | Generic EPA hub URL; no table, factor basis, fuel density, heating value, or version is recorded. Applicability to India and CO2 versus CO2e are unresolved. | **Unverified** | Seeded fuel factor; manual fuel activities. |
| Diesel Fuel Combustion | fuel | 2.680 | kgCO2e/L | Global | 2024 | US EPA GHG Emission Factors Hub | Generic EPA hub URL; no exact table/version or fuel basis is recorded. | **Unverified** | Seeded fuel factor; manual fuel activities; campus fleet inputs are separate. |
| Compressed Natural Gas (CNG) | fuel | 2.750 | kgCO2e/kg | Global | 2024 | DEFRA & IPCC Guidelines | Generic IPCC landing page; no gas composition, heating value, methane/N2O factors, or exact table is recorded. The app's CNG input basis is mass, while vehicle fuel is often billed by standard cubic metre or kg. | **Unverified** | Seeded fuel factor; manual CNG activities. |
| LPG Household Cooking Gas | fuel | 2.980 | kgCO2e/kg | Global | 2024 | IPCC & DEFRA | Generic landing pages; no exact factor table/version or distinction between CO2 and CO2e is recorded. | **Unverified** | Seeded LPG activities; cylinder conversion in `carbon.py`. |
| Municipal Solid Waste (Mixed Landfill) | waste | 0.520 | kgCO2e/kg | Global Average | 2024 | US EPA WARM / IPCC | WARM is a pathway- and material-specific life-cycle model. The code does not identify the WARM version, material composition, landfill methane capture, transport, or accounting boundary. | **Estimated** | Seeded mixed-waste activities. |
| Canteen & Kitchen Food Waste (Organic) | waste | 0.625 | kgCO2e/kg | Global | 2024 | US EPA WARM & FAO | The EPA documentation supports pathway-specific food-waste modelling, but the exact 0.625 value, pathway, WARM version, and boundary are not recorded. | **Estimated** | Seeded food-waste factor; campus food-waste API uses the same literal directly. |
| Electronic Waste (E-Waste) | waste | 18.500 | kgCO2e/kg | Global | 2024 | Global E-waste Monitor & WEEE Forum | The cited Global E-waste Monitor reports quantities and avoided emissions at global scale; it does not establish a generic 18.5 kgCO2e/kg disposal factor. No product mix, treatment route, or life-cycle boundary is recorded. | **Unverified** | Seeded e-waste activities. |
| Municipal Water Supply | **water** | 0.000344 | kgCO2e/L | India / Global | 2024 | UK DEFRA & CPCB | Assumptions say 0.344 kgCO2e/m3, which is dimensionally equal to 0.000344 kgCO2e/L. The cited URLs do not identify an exact water-supply factor, treatment boundary, utility region, or version. | **Unverified** | Seeded water activities. |

### Unit and category observations

1. Water is now a first-class `water` category. The six existing
   `Municipal Water Supply` records were reclassified in place, preserving
   factor IDs, workspace associations, and linked activity foreign keys.
   Historical activity snapshots retain their original category and emissions.
2. Bus and metro factors are described as per passenger-km in their
   assumptions and documentation, but their stored units are `kgCO2e/km`.
   The GPS UI supplies vehicle travel distance, not passenger-km, and does not
   collect occupancy. This can materially over- or under-count emissions.
3. The factor engine extracts the denominator after `/` and normalizes units
   by category. It does not validate whether `km` means vehicle-km or
   passenger-km.
4. `fuel` conversion treats `kg` as a generic base unit and treats one LPG
   cylinder as 14.2 kg. This is an assumption, not a universal conversion for
   all cylinders or regions.
5. `m3` under fuel is converted using 0.75 kg/m3 for natural gas. This is a
   mass approximation and is not a robust energy-basis conversion without
   gas composition, pressure, temperature, and standard-condition metadata.

## Other emission-affecting constants outside the factor registry

These are not rows in `emission_factors`, but they produce or materially
change displayed emissions and must be included in any correction project.

| Location | Constant | Unit/meaning | Classification | Finding |
|---|---:|---|---|---|
| `backend/app/database.py`, `create_food_waste_record` | 0.625 | kgCO2e per kg non-composted food waste | Estimated | Duplicates the registry value without reading the selected factor. |
| `backend/app/main.py`, `calculate_event` | 0.71 | kgCO2e per kWh generator electricity | Estimated | Duplicates the grid factor without using the workspace's selected factor. |
| `backend/app/main.py`, `calculate_event` | 1.5 | kgCO2e per meal served | Demonstration | No source, year, meal composition, geography, or boundary is recorded. |
| `backend/app/main.py`, `calculate_event` | 0.089 | kgCO2e per travel km/person | Unverified | Duplicates bus factor and assumes every event travel kilometre is bus passenger travel. |
| `backend/app/main.py`, `trip_stop`; `database.py`, `complete_trip` | 0.170 | kgCO2e per GPS km | Unverified | Default personal-vehicle value bypasses factor selection. |
| `backend/app/carbon.py`, `calculate_impact_equivalents` | 22 | kgCO2e absorbed per mature tree per year | Unverified | Not an emissions factor; cited in prose as an IPCC reference but no exact forestry publication is stored. |
| `backend/app/carbon.py`, `calculate_impact_equivalents` | 8.00 | INR per kWh | Demonstration | Financial tariff, not an emission factor; no tariff region, utility, or date. |
| `frontend/src/components/IndividualGpsWidget.tsx` | 102 | INR per litre | Demonstration | Display text conflicts with backend's 100 INR/L comment and is not used in the carbon calculation. |
| `backend/app/carbon.py`, `calculate_impact_equivalents` | 120 | litres of water per kg avoided CO2e | Demonstration | No source or causal basis; not an emission factor. |
| `backend/scripts/preprocess_datasets.py` | 0.710 | kgCO2e/kWh | Estimated | Duplicate grid factor used for prepared ML data; not read from the registry. |

The campus building telemetry values in
`frontend/src/components/CampusSustainabilityWidget.tsx` are demo
consumption readings, not emission factors. They should not be presented as
measured emissions without applying a verified electricity and water factor.

## Source verification findings

### Indian electricity: CEA CDM-CO2 Baseline Database

The official CEA page is:

<https://cea.nic.in/cdm-co2-baseline-view?lang=en&mappingId=234>

The page currently lists **Baseline Carbon Dioxide Emission Database Version
22.0** and a separate Version 22.0 user guide. It also lists earlier versions,
including Version 19.0 and Version 21.0. The application stores `factor_year:
2024`, while the README describes the value as CEA Version 19 and the code
description calls it an “illustrative configured reference factor.” These
metadata claims are inconsistent.

The current CEA Version 22.0 user guide reports a weighted-average Indian-grid
factor of **0.675 tCO2/MWh** for FY 2025–26, equivalent to **0.675
kgCO2/kWh**. The project value of 0.710 kg/kWh is therefore not the current
CEA value identified in this audit. It must not be labelled official without
recording the exact CEA workbook row, version, fiscal year, and selected margin.
CEA factors are normally reported in tCO2/MWh; the conversion to kgCO2/MWh and
then kgCO2/kWh must be recorded explicitly:

```text
1 tCO2/MWh = 1 kgCO2/kWh
```

The CEA Version 19 guide is also superseded: it reports a weighted-average
factor of 0.971 tCO2/MWh for FY 2022–23, not the project's 0.710 value. The
CEA source is an electricity-grid baseline source. It must not be reused for
petrol, diesel, transport, waste, water, or food-waste factors.

### Transport

The UK Government's 2024 conversion-factor publication is:

<https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024>

It provides versioned condensed and full spreadsheets and notes an October
2024 update. A generic collection URL is insufficient to identify a factor.
The application must record the workbook version, worksheet, row, vehicle
class, fuel type, occupancy basis, and whether the factor is direct-only,
well-to-wheel, or life-cycle.

The Indian Ministry of Road Transport and Highways / Rajya Sabha response
“Vehicle-wise Emission Factors for PM, NOx, HC, CO and CO2 for Vehicles
Running on Petrol, Diesel and CNG” (2021) reports vehicle exhaust factors in
**g/km**, not universal fuel factors in litres. IPCC 2006 Volume 2 provides
energy-based defaults of 69.3 tCO2/TJ for gasoline and 74.1 tCO2/TJ for
gas/diesel oil; converting those to kg/L requires fuel-specific net calorific
value and density.

The existing bus and metro values appear to be passenger-km style values, but
the app stores and applies them as km. This is the highest-priority transport
unit issue.

### Fuels

The EPA GHG Emission Factors Hub is a legitimate methodology source, but the
current code stores only the landing page. A correction requires the exact
table/version and a declared basis:

- direct combustion CO2 only, or CO2e including CH4 and N2O;
- mass, volume, or energy basis;
- US fuel properties or India-specific fuel properties;
- lower/heating value and density used for any conversion.

The values must not be described as “global” merely because the source is
from the United States.

### Waste and food waste

EPA WARM documentation is available at:

<https://www.epa.gov/waste-reduction-model/documentation-waste-reduction-model>

WARM factors vary by material and management pathway and may include
life-cycle benefits or avoided emissions. A single mixed-landfill or food
waste value is incomplete without the WARM version, material, management
pathway, methane capture assumptions, transport distance, and whether
biogenic carbon is included. The current source field does not provide those
details.

IPCC 2006 Volume 5 Chapter 4 provides composting defaults of 4 g CH4/kg wet
waste and 0.24 g N2O/kg wet waste, with dry-basis alternatives and ranges.
The Indian Carbon Market BM-T-013 composting methodology uses 0.002 t CH4/t
waste and 0.0002 t N2O/t waste. These are treatment-process factors, not a
universal 0.625 kgCO2e/kg food-landfill factor; moisture basis, pathway, and
additional electricity/fuel emissions must be specified.

### E-waste

The Global E-waste Monitor 2024 reports global e-waste quantities and
high-level avoided emissions from formal management. It does not, by itself,
support a universal 18.5 kgCO2e/kg factor for all e-waste. A product- or
treatment-specific life-cycle source is required.

## API, frontend, report, and test coverage

### Factor retrieval and calculation paths

- `GET /api/factors` returns workspace factors.
- `POST /api/factors` lets an administrator enter arbitrary factor metadata;
  it does not verify the source or factor value.
- `POST /api/factors/seed` inserts all 15 reference records only when the
  workspace has no factors.
- `POST /api/activities` selects an explicit factor or matches a factor by
  category/unit. If none is available, it creates a zero-value placeholder
  named “No verified emission factor” and stores zero emissions.
- `POST /api/electricity/calculate` selects the requested electricity factor
  or the first workspace electricity factor.
- `POST /api/trips/{trip_id}/stop` accepts a client-provided factor value and
  otherwise defaults to 0.170. It then records a ledger activity using the
  first transport factor, which can differ from the value used to complete
  the trip.
- Campus food waste and event endpoints calculate with literals rather than
  looking up workspace factors.

### Frontend

- `FactorsPage.tsx` displays stored value, unit, region, year, and source, but
  does not verify the source or classify provenance.
- `ActivityPage.tsx` retrieves compatible factors from `/api/factors` and
  displays the stored factor trail.
- `IndividualGpsWidget.tsx` contains hard-coded car, motorcycle, bus, and
  zero active-travel values and sends them to the stop endpoint.
- `CampusSustainabilityWidget.tsx` submits campus waste and event inputs; the
  backend applies the hard-coded factors.
- `DashboardPage.tsx`, analytics, CSV reports, and explanation views mostly
  display the factor snapshot stored on each activity. They do not independently
  re-validate factor provenance.

### Tests

Existing tests verify arithmetic, unit normalization, factor metadata
persistence, seeded factor availability, GPS behavior, food-waste positivity,
and report output. They do **not** currently verify:

- exact source document/version for every reference factor;
- passenger-km versus vehicle-km semantics;
- the water category mismatch;
- event and campus literals against the factor registry;
- rejection of unverified or stale source metadata;
- consistency between the factor used to complete a GPS trip and the factor
  stored in the activity ledger.

## Unsupported factors and inconsistencies

1. **No exact source citations:** Most records cite home or collection pages,
   not an exact source publication, worksheet, table, row, and version.
2. **CEA version mismatch:** Code says year 2024, README says Version 19, and
   the official page currently lists Version 22.0.
3. **Water is stored as waste:** The factor is semantically misclassified and
   excluded from the API category allow-list.
4. **Passenger-km treated as km:** Bus, metro, and event travel factors lack
   occupancy and mode semantics.
5. **Duplicate logic:** Food waste, event electricity, event travel, GPS
   default transport, and ML preprocessing duplicate registry values.
6. **Client-controlled GPS factor:** A client can submit a factor value to the
   trip-stop endpoint.
7. **First-factor selection:** Electricity and GPS ledger paths may use the
   first factor rather than the factor used for the calculation.
8. **Weak verification flag:** `analytics.factor_trail()` treats a factor as
   verified unless its name is exactly “No verified emission factor.” A
   user-entered factor with a fake or generic source is therefore reported as
   verified.
9. **Demo data mixed with measured data:** Campus telemetry and some financial
   and event constants are presented in production-looking dashboards without
   a clear demo classification.
10. **Boundary mixing:** Direct combustion, location-based electricity,
    passenger travel, life-cycle waste, and embodied e-waste values are mixed
    in one `emissions_kg` total without a consistent boundary label.

## Recommended corrections

Do not apply these corrections as part of this audit. They are the required
follow-up design and implementation work.

### P0 — prevent incorrect calculations

1. Replace bus/metro/GPS transport units with explicit `vehicle-km`,
   `passenger-km`, or a model that requires occupancy.
2. Stop using hard-coded event, food-waste, GPS, and ML factors. Resolve
   factors through a single factor service/registry and persist the exact
   factor ID and snapshot.
3. Prevent a client-supplied GPS factor from overriding an administrator-
   selected workspace factor.
4. Fix the water category model. Either add a first-class `water` category
   with API/UI support or remove the water record until it has a supported
   path.
5. Make the calculation boundary explicit: direct CO2, CO2e, location-based,
   market-based, well-to-wheel, and life-cycle must not be silently combined.

### P1 — make provenance auditable

1. Add source publication title, version, publisher, publication date,
   worksheet/table/row, retrieval date, boundary, geography, and unit-basis
   fields to factor metadata.
2. Replace generic URLs with stable links to the original CEA workbook/user
   guide, DEFRA workbook, EPA table/methodology, and WARM chapter.
3. Record the exact CEA version and fiscal year. Reconcile the current
   0.710 value against the current CEA workbook before calling it official.
4. Add a provenance classification field rather than inferring verification
   from the factor name.

### P2 — improve model and UX consistency

1. Add source/version/unit tests for every seeded factor.
2. Add tests for passenger-km conversions, water category behavior, event
   calculations, and duplicate-factor consistency.
3. Label demo campus telemetry and illustrative constants as demo/estimated.
4. Separate financial tariffs and impact-equivalent conversions from emission
   factors.
5. Version seeded factors so later seed updates do not silently alter an
   existing workspace.

## Missing information required before approving values

- Exact CEA database version and workbook row for the electricity factor.
- The fiscal year and whether the electricity factor is simple operating
  margin, weighted average, or combined margin.
- Exact transport source rows, occupancy assumptions, and vehicle-km versus
  passenger-km basis.
- Whether fuel factors include only CO2 or full CO2e and which fuel properties
  were used.
- Exact WARM version, material mix, management pathway, methane capture, and
  life-cycle boundary.
- A defensible product/treatment basis for e-waste.
- Indian municipal water region, treatment energy, distribution boundary, and
  source publication.
- Source and boundary for meal, tree, and water-equivalent constants.

## Audit conclusion

The application has a useful traceability structure, but the current factor
set should be treated as **demonstration/estimated data rather than a verified
Indian emissions inventory**. The highest risks are transport unit semantics,
the water category error, duplicate hard-coded factors, and incomplete source
versioning. No factor values should be changed until the exact original
documents and boundaries are attached to each factor record.

## Sources consulted

- Central Electricity Authority, CDM-CO2 Baseline Database page:
  <https://cea.nic.in/cdm-co2-baseline-view?lang=en&mappingId=234>
- CEA Version 22.0 user guide:
  <https://cea.nic.in/api/cdm-report-version/view-pdf/en/82>
- CEA Version 19.0 database/user guide:
  <https://cea.nic.in/api/cdm-report-version/view-pdf/en/74>
- UK Government, Greenhouse gas reporting: conversion factors 2024:
  <https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024>
- Indian Government Open Data, vehicle-wise petrol/diesel/CNG exhaust factors:
  <https://punjab.data.gov.in/resource/vehicle-wise-emission-factors-pm-nox-hc-co-and-co2-vehicles-running-petrol-diesel-and-cng>
- IPCC 2006 Guidelines, Volume 2: Energy:
  <https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_0_Cover.pdf>
- IPCC 2006 Guidelines, Volume 5, Chapter 4: Biological treatment:
  <https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/5_Volume5/V5_4_Ch4_Bio_Treat.pdf>
- Indian Carbon Market BM-T-013 Composting methodology:
  <https://indiancarbonmarket.gov.in/storage/pages/177942847872.pdf>
- US EPA, Waste Reduction Model documentation:
  <https://www.epa.gov/waste-reduction-model/documentation-waste-reduction-model>
- Global E-waste Monitor 2024:
  <https://www.itu.int/en/ITU-D/Environment/Documents/Publications/2025/d-gen-e_waste.01-2024-pdf-e.pdf>
- IPCC National Greenhouse Gas Inventories:
  <https://www.ipcc-nggip.iges.or.jp/>
- US EPA GHG Emission Factors Hub:
  <https://www.epa.gov/climateleadership/ghg-emission-factors-hub>
