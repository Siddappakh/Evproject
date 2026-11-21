from pathlib import Path


ML_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ML_ROOT.parents[1]
MODEL_DIR = Path(__import__("os").environ.get("GREENTRACK_MODEL_DIR", str(REPOSITORY_ROOT / "models")))
MODEL_DIR.mkdir(parents=True, exist_ok=True)
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_model.joblib"
EMISSION_MODEL_PATH = MODEL_DIR / "emission_model.joblib"
FORECAST_MODEL_PATH = MODEL_DIR / "forecasting_model.joblib"
METADATA_PATH = MODEL_DIR / "model_metadata.json"
DATASET_VERSION = "activity-ledger-v1"

