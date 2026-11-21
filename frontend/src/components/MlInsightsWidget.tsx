import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { MlAnomaly, MlForecastPoint, MlModelStatus, MlPrediction } from "../types/api";

export function MlInsightsWidget({ period }: { period: string }) {
  const [status, setStatus] = useState<MlModelStatus | null>(null);
  const [prediction, setPrediction] = useState<MlPrediction | null>(null);
  const [anomalies, setAnomalies] = useState<MlAnomaly[]>([]);
  const [forecast, setForecast] = useState<MlForecastPoint[]>([]);
  const [metrics, setMetrics] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const modelStatus = await api.getMlModelStatus();
        if (!active) return;
        setStatus(modelStatus);
        const modelMetrics = await api.getMlModelMetrics();
        if (!active) return;
        setMetrics(modelMetrics.metrics);
        if (!modelStatus.available) return;
        const [predicted, detected, projected] = await Promise.all([
          api.predictEmissions({ period }),
          api.detectMlAnomalies({ period }),
          api.forecastMlEmissions(3, period),
        ]);
        if (active) {
          setPrediction(predicted.predictions[0] ?? null);
          setAnomalies(detected.anomalies.filter((item) => item.is_anomaly));
          setForecast(projected.forecast);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "ML insights could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [period, retryToken]);

  return (
    <section className="surface-card mb-5 p-5" aria-label="Machine learning insights">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600">ML INSIGHTS</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-800">Predictions and anomaly signals</h2>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status?.available ? "bg-cyan-50 text-cyan-700" : "bg-amber-50 text-amber-700"}`}>
          {loading ? "Loading models" : status?.available ? "Models ready" : "Models not trained"}
        </span>
      </div>
      {error && <p className="mt-3 text-xs text-amber-700">{error}</p>}
      {error && <button className="btn-secondary mt-3" onClick={() => setRetryToken((value) => value + 1)}>Retry</button>}
      {loading && <p className="mt-4 text-sm text-slate-500">Loading model status and evaluation metrics…</p>}
      {!status?.available && !error && (
        <p className="mt-3 text-sm text-slate-500">Train the documented models to replace this status with measured predictions.</p>
      )}
      {status?.available && (
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500">Predicted first activity</p>
            <p className="mt-1 text-xl font-bold text-slate-800">{prediction ? `${prediction.predicted_emissions_kg} kgCO2e` : "No activity"}</p>
            <p className="mt-1 text-xs text-slate-500">Gradient Boosting estimate</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500">Isolation Forest alerts</p>
            <p className="mt-1 text-xl font-bold text-slate-800">{anomalies.length}</p>
            <p className="mt-1 text-xs text-slate-500">Unusual records in {period}; not causal explanations</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500">Next forecast</p>
            <p className="mt-1 text-xl font-bold text-slate-800">{forecast[0] ? `${forecast[0].predicted_emissions_kg} kgCO2e` : "Unavailable"}</p>
            <p className="mt-1 text-xs text-slate-500">{forecast[0]?.period ?? "No forecast period"} · estimated</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 sm:col-span-3">
            <p className="text-xs text-slate-500">Measured validation</p>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              Emission R² {String((metrics?.emission?.metrics && (metrics.emission.metrics as { r2?: unknown }).r2) ?? "n/a")}
              {" · "}Forecast backtest R² {String((metrics?.forecast?.validation_metrics && (metrics.forecast.validation_metrics as { r2?: unknown }).r2) ?? "n/a")}
            </p>
            <p className="mt-1 text-xs text-slate-500">{String(metrics?.forecast?.validation ?? "Validation metadata unavailable")}</p>
          </div>
        </div>
      )}
    </section>
  );
}
