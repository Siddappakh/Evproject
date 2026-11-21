import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";

export function UrbanEvForecastWidget() {
  const [zones, setZones] = useState<string[]>([]);
  const [zone, setZone] = useState("");
  const [info, setInfo] = useState<{ records: number; zones: number; start: string; end: string } | null>(null);
  const [forecast, setForecast] = useState<Awaited<ReturnType<typeof api.getUrbanEvForecast>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.getUrbanEvInfo(), api.getUrbanEvZones()])
      .then(([datasetInfo, availableZones]) => {
        setInfo(datasetInfo);
        setZones(availableZones);
        setZone(availableZones[0] ?? "");
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "UrbanEV data could not be loaded."));
  }, []);

  const loadForecast = () => {
    setError(null);
    void api.getUrbanEvForecast(zone || undefined, 24)
      .then(setForecast)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Forecast could not be loaded."));
  };

  const chartData = [
    ...(forecast?.historical.slice(-48).map((point) => ({ time: point.recorded_at, actual: point.actual_kwh, predicted: point.predicted_kwh })) ?? []),
    ...(forecast?.forecast.map((point) => ({ time: point.recorded_at, predicted: point.predicted_kwh })) ?? []),
  ];

  return (
    <section className="surface-card mb-5 p-5" aria-label="UrbanEV charging demand forecast">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600">URBANEV CHARGING DEMAND</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-800">Actual versus predicted zone volume</h2>
          {info && <p className="mt-1 text-xs text-slate-500">{info.records.toLocaleString()} imported records · {info.zones} zones · {info.start} to {info.end}</p>}
        </div>
        <div className="flex gap-2">
          <select className="rounded-lg border border-slate-200 px-2 py-2 text-xs" value={zone} onChange={(event) => setZone(event.target.value)} aria-label="UrbanEV zone">
            {zones.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <button className="btn-primary" onClick={loadForecast}>Forecast</button>
        </div>
      </div>
      {error && <p className="mt-3 text-xs text-amber-700">{error}</p>}
      {chartData.length > 0 ? (
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="actual" stroke="#397BFF" dot={false} name="Actual kWh" />
              <Line type="monotone" dataKey="predicted" stroke="#A855F7" dot={false} name="Predicted kWh" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : <p className="mt-6 text-sm text-slate-500">Select a zone and request a forecast to load real UrbanEV data.</p>}
      {forecast && <p className="mt-3 text-xs text-slate-500">MAE {forecast.metrics.mae_kwh} kWh · RMSE {forecast.metrics.rmse_kwh} kWh · MAPE {forecast.metrics.mape_percent}% · {forecast.warning}</p>}
    </section>
  );
}
