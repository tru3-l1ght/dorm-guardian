import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

type SensorReading = {
  id: number;
  device_id: string;
  temperature_c: number;
  humidity_percent: number;
  air_quality: number;
  created_at: string;
};

type FanState = {
  is_on: boolean;
  mode: string;
  reason: string;
  updated_at: string;
};

type Alert = {
  id: number;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
  resolved_at: string | null;
};

type HealthStatus = {
  status: string;
  service: string;
};

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  });
}

function getAirQualityLabel(value: number): string {
  if (value >= 1800) return "Poor";
  if (value >= 1000) return "Moderate";
  return "Good";
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [latestReading, setLatestReading] = useState<SensorReading | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [fanState, setFanState] = useState<FanState | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboardData() {
    try {
      const [healthData, latestData, historyData, fanData, alertsData] =
        await Promise.all([
          fetchJson<HealthStatus>(`${API_BASE_URL}/api/health`),
          fetchJson<SensorReading | null>(`${API_BASE_URL}/api/readings/latest`),
          fetchJson<SensorReading[]>(`${API_BASE_URL}/api/readings/history?limit=40`),
          fetchJson<FanState | null>(`${API_BASE_URL}/api/fan/status`),
          fetchJson<Alert[]>(`${API_BASE_URL}/api/alerts?limit=10`),
        ]);

      setHealth(healthData);
      setLatestReading(latestData);
      setHistory(historyData);
      setFanState(fanData);
      setAlerts(alertsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function resolveAlert(alertId: number) {
    try {
      await fetchJson<Alert>(`${API_BASE_URL}/api/alerts/${alertId}/resolve`);
      await loadDashboardData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resolve alert");
    }
  }

  useEffect(() => {
    loadDashboardData();

    const intervalId = window.setInterval(() => {
      loadDashboardData();
    }, 5000);

    return () => window.clearInterval(intervalId);
  }, []);

  const chartData = useMemo(() => {
    return history.map((reading) => ({
      time: formatTime(reading.created_at),
      temperature: reading.temperature_c,
      humidity: reading.humidity_percent,
      airQuality: reading.air_quality,
    }));
  }, [history]);

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Dorm Guardian Mock Dashboard</p>
          <h1>Smart Room Monitor</h1>
          <p className="subtitle">
            Simulated STM32 readings flowing into FastAPI, SQLite, fan automation,
            and alert logic.
          </p>
        </div>

        <div className="status-pill">
          <span className={health?.status === "ok" ? "dot online" : "dot offline"} />
          {health?.status === "ok" ? "Backend online" : "Backend offline"}
        </div>
      </section>

      {error && (
        <section className="error-card">
          <strong>Connection issue:</strong> {error}
        </section>
      )}

      <section className="grid cards-grid">
        <div className="card metric-card">
          <p className="card-label">Temperature</p>
          <h2>{latestReading ? `${latestReading.temperature_c.toFixed(1)}°C` : "—"}</h2>
          <p className="muted">
            {latestReading ? `Updated ${formatTime(latestReading.created_at)}` : "No readings yet"}
          </p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Humidity</p>
          <h2>
            {latestReading ? `${latestReading.humidity_percent.toFixed(1)}%` : "—"}
          </h2>
          <p className="muted">Mock environmental reading</p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Air Quality</p>
          <h2>{latestReading ? latestReading.air_quality.toFixed(0) : "—"}</h2>
          <p className="muted">
            {latestReading ? getAirQualityLabel(latestReading.air_quality) : "No reading"}
          </p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Fan</p>
          <h2 className={fanState?.is_on ? "fan-on" : "fan-off"}>
            {fanState ? (fanState.is_on ? "ON" : "OFF") : "—"}
          </h2>
          <p className="muted">{fanState?.reason ?? "Waiting for fan state"}</p>
        </div>
      </section>

      <section className="grid main-grid">
        <div className="card chart-card">
          <div className="section-header">
            <div>
              <p className="card-label">Sensor History</p>
              <h3>Recent Room Readings</h3>
            </div>
            <p className="muted">{history.length} points</p>
          </div>

          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" minTickGap={20} />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  name="Temperature °C"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="humidity"
                  name="Humidity %"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card alerts-card">
          <div className="section-header">
            <div>
              <p className="card-label">Alerts</p>
              <h3>Active Events</h3>
            </div>
            <span className="alert-count">{alerts.length}</span>
          </div>

          <div className="alerts-list">
            {alerts.length === 0 && (
              <p className="empty-state">No active alerts right now.</p>
            )}

            {alerts.map((alert) => (
              <div key={alert.id} className={`alert-item ${alert.severity}`}>
                <div>
                  <p className="alert-title">{alert.title}</p>
                  <p className="alert-message">{alert.message}</p>
                  <p className="muted">
                    {alert.alert_type} · {formatDateTime(alert.created_at)}
                  </p>
                </div>

                <button onClick={() => resolveAlert(alert.id)}>Resolve</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card raw-card">
        <p className="card-label">Latest Raw Reading</p>
        <pre>{JSON.stringify(latestReading, null, 2)}</pre>
      </section>
    </main>
  );
}

export default App;