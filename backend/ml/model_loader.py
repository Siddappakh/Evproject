from __future__ import annotations

import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from .config import ANOMALY_MODEL_PATH, EMISSION_MODEL_PATH, FORECAST_MODEL_PATH, METADATA_PATH
from .config import MODEL_DIR


def _load(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Model artifact is not available: {path}")
    return joblib.load(path)


def _artifact_status(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"available": False, "loaded": False, "path": str(path)}
    if not path.exists():
        result["error"] = "Artifact file does not exist."
        return result
    try:
        _load(path)
    except (
        OSError,
        EOFError,
        ValueError,
        ImportError,
        AttributeError,
        KeyError,
        pickle.UnpicklingError,
    ) as error:
        result["error"] = f"{type(error).__name__}: {error}"
        return result
    result["available"] = True
    result["loaded"] = True
    return result


@lru_cache(maxsize=3)
def load_anomaly_model() -> Any:
    return _load(ANOMALY_MODEL_PATH)


@lru_cache(maxsize=3)
def load_emission_model() -> Any:
    return _load(EMISSION_MODEL_PATH)


@lru_cache(maxsize=3)
def load_forecast_model() -> Any:
    return _load(FORECAST_MODEL_PATH)


def model_status() -> dict[str, object]:
    artifacts = {
        "anomaly": ANOMALY_MODEL_PATH,
        "emission": EMISSION_MODEL_PATH,
        "forecast": FORECAST_MODEL_PATH,
    }
    models = {name: _artifact_status(path) for name, path in artifacts.items()}
    return {
        "available": all(bool(model["loaded"]) for model in models.values()),
        "models": models,
        "metadata": json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        if METADATA_PATH.exists()
        else None,
    }


@lru_cache(maxsize=1)
def load_urbanev_demand_model() -> Any:
    return _load(MODEL_DIR / "urbanev_demand_model.joblib")


def urbanev_demand_status() -> dict[str, object]:
    path = MODEL_DIR / "urbanev_demand_model.joblib"
    metadata = MODEL_DIR / "urbanev_demand_metadata.json"
    artifact = _artifact_status(path)
    return {
        "available": bool(artifact["loaded"]),
        "artifact": artifact,
        "artifact_path": str(path),
        "metadata": json.loads(metadata.read_text(encoding="utf-8")) if metadata.exists() else None,
    }
