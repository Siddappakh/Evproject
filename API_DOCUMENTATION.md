# Factor API

Factor records include `value`, `unit`, `gas_basis` (`CO2` or `CO2e`),
`region`, `factor_year`, optional `effective_start`/`effective_end`,
`source_publication`, `methodology`, `classification`, and
`last_verified_date`. Electricity factors are selected by the activity date.
For dates after the latest published factor, the API uses the latest factor
with `classification: "proxy"` rather than presenting it as a new official
annual factor.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/factors` | List workspace factors, optionally filtered by category |
| POST | `/api/factors` | Add a factor with provenance metadata |
| POST | `/api/factors/seed` | Add missing reference factors without replacing existing records |

Transport factors distinguish `vehicle-km` from `passenger-km`. Public
transport calculations require passenger-km; the application does not infer
occupancy. Water factors use the `water` category rather than `waste`.

# ML API

All ML routes require an authenticated, onboarded workspace and use the existing
session/CSRF protection.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/ml/model-status` | Artifact availability and metadata |
| GET | `/api/ml/model-metrics` | Training metrics recorded in `models/model_metadata.json` |
| POST | `/api/ml/predict-emissions` | Predict activity emissions; accepts optional `period` and `activity_ids` |
| POST | `/api/ml/detect-anomalies` | Return Isolation Forest scores and flags |
| POST | `/api/ml/forecast-emissions` | Forecast 1-24 future monthly periods |
| GET | `/api/urbanev/info` | Imported UrbanEV dataset coverage and counts |
| GET | `/api/urbanev/data` | Authenticated historical UrbanEV records, optionally by zone |
| GET | `/api/urbanev/zones` | Available imported zone identifiers |
| GET | `/api/urbanev/model-status` | Charging-demand model artifact status |
| GET | `/api/urbanev/metrics` | Time-split charging-demand evaluation metrics |
| POST | `/api/urbanev/forecast` | Actual history and future zone charging-volume forecast |

Prediction and forecast values are explicitly marked as estimates. If a model has
not been trained, prediction routes return `503` with the training command rather
than returning a success-shaped fallback.

UrbanEV demand forecasts use the imported Shenzhen dataset and are not
India-specific. The model target is zone-hour charging volume in kWh, and the
training split precedes the testing split chronologically.
