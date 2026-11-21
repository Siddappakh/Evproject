from pathlib import Path

import pytest

from backend.ml.train_anomaly_model import train as train_anomaly
from backend.ml.train_emission_model import train as train_emission
from backend.ml.train_forecasting_model import train as train_forecast
from backend.ml import model_loader


def activity_records(count: int = 16) -> list[dict[str, object]]:
    return [
        {
            "id": str(index),
            "period": f"2026-{index // 4 + 1:02d}",
            "activity_date": f"2026-{index // 4 + 1:02d}-{index % 4 + 1:02d}",
            "category": "electricity" if index % 2 else "transport",
            "quantity": 100 + index,
            "unit": "kWh" if index % 2 else "km",
            "reporting_unit": "Test",
            "factor_value": 0.71 if index % 2 else 0.17,
            "factor_year": 2024,
            "emissions_kg": 71 + index,
        }
        for index in range(count)
    ]


def test_training_writes_all_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GREENTRACK_MODEL_DIR", str(tmp_path))
    from backend.ml import config

    anomaly = train_anomaly(activity_records(), tmp_path / "anomaly.joblib")
    emission = train_emission(activity_records(), tmp_path / "emission.joblib")
    forecast = train_forecast(activity_records(), tmp_path / "forecast.joblib")
    assert anomaly["records"] == 16
    assert emission["metrics"]["mae_kg"] >= 0
    assert emission["validation"] == "chronological 75/25 holdout"
    assert forecast["periods"] == 4
    assert forecast["validation_metrics"]["mae_kg"] >= 0


def test_model_status_requires_loadable_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(model_loader, "ANOMALY_MODEL_PATH", tmp_path / "anomaly.joblib")
    monkeypatch.setattr(model_loader, "EMISSION_MODEL_PATH", tmp_path / "emission.joblib")
    monkeypatch.setattr(model_loader, "FORECAST_MODEL_PATH", tmp_path / "forecast.joblib")
    monkeypatch.setattr(model_loader, "METADATA_PATH", tmp_path / "metadata.json")
    (tmp_path / "anomaly.joblib").write_text("not a model", encoding="utf-8")
    (tmp_path / "emission.joblib").write_text("not a model", encoding="utf-8")
    (tmp_path / "forecast.joblib").write_text("not a model", encoding="utf-8")

    status = model_loader.model_status()

    assert status["available"] is False
    assert all(model["loaded"] is False for model in status["models"].values())
