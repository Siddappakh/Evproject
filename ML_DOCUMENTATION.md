# GreenTrack ML

GreenTrack adds a reproducible ML subsystem under `backend/ml/`.

## Models

- **Isolation Forest** detects unusual combinations of activity quantity, factor,
  category, unit, reporting unit, and calendar features. Its score is an alert signal,
  not a causal explanation.
- **Gradient Boosting Regressor** predicts `emissions_kg` from activity inputs. The
  training command reports MAE, RMSE, R2, and a mean baseline MAE on a chronological
  75/25 held-out split, so evaluation reflects predicting later records from earlier ones.
- **Ridge time trend** forecasts monthly totals after aggregating records by `period`.
  Forecasts are estimates and use only time-based features. Training reports a
  chronological last-period backtest to make its unseen-period performance visible.
- **UrbanEV charging demand model** predicts zone-hour charging volume using zone,
  hour, weekday, month, occupancy, duration, electricity price, service price, and
  temperature. It uses a chronological 80/20 split and is available through the
  `/api/urbanev/*` endpoints.

## Training

From the repository root, after preparing a CSV:

```powershell
python -m backend.ml.train_all data\processed\activities.csv
```

Artifacts are written to `models\`. Set `GREENTRACK_MODEL_DIR` to use another
artifact directory. The API never retrains during a request.

## API

Authenticated routes are available at `/api/ml/model-status`,
`/api/ml/model-metrics`, `/api/ml/predict-emissions`,
`/api/ml/detect-anomalies`, and `/api/ml/forecast-emissions`.
Untrained models return HTTP 503 rather than fabricated values.

## Limitations

Model quality depends on the quantity, coverage, and traceability of supplied
activity data. No causal inference, SHAP explanation, or accuracy claim is made
when the corresponding artifact and evaluation metadata are absent.

UrbanEV is Shenzhen public charging data under CC0. Its `volume.csv` target is
derived from charging-pile rated power, so it is charging-demand data rather than
direct vehicle-side meter data.
