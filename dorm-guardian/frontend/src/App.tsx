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

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:8000`;

type SensorReading = {
  id: number;
  timestamp: string;
  temperature: number | null;
  humidity: number | null;
  pressure: number | null;
  light: number | null;
  fan_status: boolean;
  source: string;
};

type HealthStatus = {
  status: string;
  service?: string;
};

type CameraStatus = {
  camera_index: number;
  enabled?: boolean;
  available: boolean | null;
  message?: string;
};

type MotionStatus = {
  motion_detected: boolean;
  last_motion_time: string | null;
  motion_area: number;
};

type MotionEvent = {
  id: number;
  timestamp: string;
  motion_area: number;
  source: string;
};

type MotionSummary = {
  count_today: number;
  latest_event: MotionEvent | null;
};

type Alert = {
  id: number;
  timestamp: string;
  type: string;
  severity: string;
  message: string;
  source: string;
};

type AlertSummary = {
  count_today: number;
  warning_count_today: number;
  latest_alert: Alert | null;
};

type AuthStatus = {
  authenticated: boolean;
  auth_enabled: boolean;
};

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    credentials: "include",
  });

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

function formatMotionTime(value: string | null): string {
  if (!value) return "No motion yet";

  return new Date(value.replace(" ", "T")).toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  });
}

function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

function CameraPanel() {
  const [previewEnabled, setPreviewEnabled] = useState(false);
  const [motionPreviewEnabled, setMotionPreviewEnabled] = useState(false);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  async function loadCameraStatus() {
    try {
      const data = await fetchJson<CameraStatus>(
        `${API_BASE_URL}/api/camera/status`
      );
      setCameraStatus(data);
      setCameraError(null);
    } catch (err) {
      setCameraError(err instanceof Error ? err.message : "Unknown error");
      setCameraStatus(null);
    }
  }

  useEffect(() => {
    loadCameraStatus();
  }, []);

  const backendCameraDisabled =
    cameraStatus?.enabled === false || cameraStatus?.available === null;

  const canStartPreview =
    cameraStatus &&
    cameraStatus.enabled !== false &&
    cameraStatus.available === true;

  function startNormalPreview() {
    setMotionPreviewEnabled(false);
    setPreviewEnabled((value) => !value);
  }

  function startMotionPreview() {
    setPreviewEnabled(false);
    setMotionPreviewEnabled((value) => !value);
  }

  const streamUrl = motionPreviewEnabled
    ? `${API_BASE_URL}/api/camera/motion-stream`
    : `${API_BASE_URL}/api/camera/stream`;

  const isAnyPreviewEnabled = previewEnabled || motionPreviewEnabled;

  return (
    <section className="card camera-card">
      <div className="section-header">
        <div>
          <p className="card-label">Camera Preview</p>
          <h3>Live Room Camera</h3>
          <p className="muted">
            Privacy-safe: the stream only loads after you click start.
          </p>
        </div>

        <div className="camera-actions">
          <button
            className={`camera-toggle ${previewEnabled ? "danger" : ""}`}
            disabled={!canStartPreview}
            onClick={startNormalPreview}
          >
            {previewEnabled ? "Stop Camera" : "Start Camera"}
          </button>

          <button
            className={`camera-toggle ${
              motionPreviewEnabled ? "danger" : ""
            }`}
            disabled={!canStartPreview}
            onClick={startMotionPreview}
          >
            {motionPreviewEnabled ? "Stop Motion View" : "Start Motion View"}
          </button>
        </div>
      </div>

      {cameraError && (
        <div className="camera-message error">
          Camera status error: {cameraError}
        </div>
      )}

      {backendCameraDisabled && (
        <div className="camera-message">
          {cameraStatus?.message ?? "Camera is disabled for privacy."}
        </div>
      )}

      {cameraStatus?.enabled !== false && cameraStatus?.available === false && (
        <div className="camera-message error">
          Camera is enabled in backend, but no camera was detected.
        </div>
      )}

      <div className="camera-frame">
        {isAnyPreviewEnabled && canStartPreview ? (
          <img
            src={streamUrl}
            alt={
              motionPreviewEnabled
                ? "Live motion detection stream"
                : "Live camera stream"
            }
            className="camera-stream"
          />
        ) : (
          <div className="camera-placeholder">
            <p>Camera preview is off</p>
            <span>
              {canStartPreview
                ? "Start camera or motion view to open the stream."
                : "Enable camera in backend first."}
            </span>
          </div>
        )}
      </div>

      <div className="camera-meta">
        <span>Camera index: {cameraStatus?.camera_index ?? "—"}</span>
        <span>
          Status:{" "}
          {cameraStatus
            ? cameraStatus.enabled === false
              ? "disabled"
              : cameraStatus.available
              ? "available"
              : "unavailable"
            : "unknown"}
        </span>
        <span>
          Mode:{" "}
          {motionPreviewEnabled
            ? "motion detection"
            : previewEnabled
            ? "normal preview"
            : "off"}
        </span>
      </div>
    </section>
  );
}

function MotionStatusCard() {
  const [motionStatus, setMotionStatus] = useState<MotionStatus | null>(null);
  const [motionError, setMotionError] = useState<string | null>(null);

  async function loadMotionStatus() {
    try {
      const data = await fetchJson<MotionStatus>(
        `${API_BASE_URL}/api/camera/motion-status`
      );

      setMotionStatus(data);
      setMotionError(null);
    } catch (err) {
      setMotionError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  useEffect(() => {
    loadMotionStatus();

    const intervalId = window.setInterval(() => {
      loadMotionStatus();
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <div
      className={`card metric-card motion-card ${
        motionStatus?.motion_detected ? "motion-active" : ""
      }`}
    >
      <p className="card-label">Live Motion</p>

      <h2>{motionStatus?.motion_detected ? "Detected" : "Clear"}</h2>

      {motionError ? (
        <p className="muted">Motion status unavailable: {motionError}</p>
      ) : (
        <>
          <p className="muted">
            Last motion:{" "}
            {formatMotionTime(motionStatus?.last_motion_time ?? null)}
          </p>
          <p className="muted">
            Motion area: {motionStatus?.motion_area ?? 0}
          </p>
        </>
      )}
    </div>
  );
}

function AlertsPanel() {
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadAlerts() {
    try {
      const [summaryData, alertsData] = await Promise.all([
        fetchJson<AlertSummary>(`${API_BASE_URL}/api/alerts/summary`),
        fetchJson<Alert[]>(`${API_BASE_URL}/api/alerts?limit=10`),
      ]);

      setSummary(summaryData);
      setAlerts(alertsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  useEffect(() => {
    loadAlerts();

    const intervalId = window.setInterval(() => {
      loadAlerts();
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <section className="card alerts-card">
      <div className="section-header">
        <div>
          <p className="card-label">Guardian Alerts</p>
          <h3>Recent Alerts</h3>
        </div>

        <div className="alert-count">{summary?.count_today ?? 0}</div>
      </div>

      {error && (
        <div className="camera-message error">Alerts unavailable: {error}</div>
      )}

      <div className="alerts-list">
        <div
          className={`alert-item ${
            summary?.warning_count_today ? "warning" : "info"
          }`}
        >
          <div>
            <p className="alert-title">Alert Summary</p>
            <p className="alert-message">
              {summary
                ? `${summary.count_today} alerts today · ${summary.warning_count_today} warnings`
                : "Loading alert summary..."}
            </p>
          </div>
        </div>

        <div className="alert-item info">
          <div>
            <p className="alert-title">Latest Alert</p>
            <p className="alert-message">
              {summary?.latest_alert
                ? `${formatDateTime(summary.latest_alert.timestamp)} · ${
                    summary.latest_alert.message
                  }`
                : "No alerts yet"}
            </p>
          </div>
        </div>

        {alerts.length === 0 ? (
          <p className="empty-state">No alerts saved yet.</p>
        ) : (
          alerts.map((alert) => (
            <div
              className={`alert-item ${
                alert.severity === "warning" ? "warning" : "info"
              }`}
              key={alert.id}
            >
              <div>
                <p className="alert-title">
                  {alert.type.replaceAll("_", " ")} · {alert.severity}
                </p>
                <p className="alert-message">
                  {formatDateTime(alert.timestamp)} · {alert.message} ·{" "}
                  {alert.source}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function MotionEventsPanel() {
  const [summary, setSummary] = useState<MotionSummary | null>(null);
  const [events, setEvents] = useState<MotionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadMotionEvents() {
    try {
      const [summaryData, eventsData] = await Promise.all([
        fetchJson<MotionSummary>(`${API_BASE_URL}/api/motion/summary`),
        fetchJson<MotionEvent[]>(`${API_BASE_URL}/api/motion/events?limit=8`),
      ]);

      setSummary(summaryData);
      setEvents(eventsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  useEffect(() => {
    loadMotionEvents();

    const intervalId = window.setInterval(() => {
      loadMotionEvents();
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <section className="card motion-events-card">
      <div className="section-header">
        <div>
          <p className="card-label">Motion Event History</p>
          <h3>Saved Motion Events</h3>
        </div>

        <div className="alert-count">{summary?.count_today ?? 0}</div>
      </div>

      {error && (
        <div className="camera-message error">
          Motion events unavailable: {error}
        </div>
      )}

      <div className="alerts-list">
        <div className="alert-item info">
          <div>
            <p className="alert-title">Latest Saved Motion</p>
            <p className="alert-message">
              {summary?.latest_event
                ? `${formatDateTime(summary.latest_event.timestamp)} · area ${
                    summary.latest_event.motion_area
                  }`
                : "No saved motion events yet"}
            </p>
          </div>
        </div>

        {events.length === 0 ? (
          <p className="empty-state">No motion events saved yet.</p>
        ) : (
          events.map((event) => (
            <div className="alert-item" key={event.id}>
              <div>
                <p className="alert-title">Motion event #{event.id}</p>
                <p className="alert-message">
                  {formatDateTime(event.timestamp)} · area {event.motion_area} ·{" "}
                  {event.source}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}


function LoginScreen({ onLoginSuccess }: { onLoginSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setLoginError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        throw new Error("Invalid password");
      }

      onLoginSuccess();
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page login-page">
      <section className="card login-card">
        <p className="eyebrow">Dorm Guardian</p>
        <h1>Login required</h1>
        <p className="subtitle">
          Enter the dashboard password to access sensors, camera, motion events,
          and alerts.
        </p>

        <form className="login-form" onSubmit={handleLogin}>
          <input
            className="login-input"
            type="password"
            placeholder="Dashboard password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />

          <button className="camera-toggle" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Checking..." : "Login"}
          </button>
        </form>

        {loginError && (
          <div className="camera-message error">{loginError}</div>
        )}
      </section>
    </main>
  );
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [latestReading, setLatestReading] = useState<SensorReading | null>(null);
  const [history, setHistory] = useState<SensorReading[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  async function checkAuthStatus() {
    try {
      const data = await fetchJson<AuthStatus>(`${API_BASE_URL}/api/auth/status`);
      setAuthenticated(data.authenticated);
    } catch {
      setAuthenticated(false);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogout() {
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    setAuthenticated(false);
    setLatestReading(null);
    setHistory([]);
  }

  async function loadDashboardData() {
    try {
      const [healthData, latestData, historyData] = await Promise.all([
        fetchJson<HealthStatus>(`${API_BASE_URL}/api/health`),
        fetchJson<SensorReading | { status: string }>(
          `${API_BASE_URL}/api/sensors/latest`
        ),
        fetchJson<SensorReading[]>(
          `${API_BASE_URL}/api/sensors/history?limit=40`
        ),
      ]);

      setHealth(healthData);

      if ("status" in latestData && latestData.status === "no_data") {
        setLatestReading(null);
      } else {
        setLatestReading(latestData as SensorReading);
      }

      setHistory(historyData);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";

      if (message.includes("401")) {
        setAuthenticated(false);
        setError("Authentication required. Please log in again.");
      } else {
        setError(message);
      }
    }
  }

  useEffect(() => {
    checkAuthStatus();
  }, []);

  useEffect(() => {
    if (!authenticated) return;

    loadDashboardData();

    const intervalId = window.setInterval(() => {
      loadDashboardData();
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [authenticated]);

  const chartData = useMemo(() => {
    return [...history].reverse().map((reading) => ({
      time: formatTime(reading.timestamp),
      temperature: reading.temperature,
      humidity: reading.humidity,
      pressure: reading.pressure,
      light: reading.light,
    }));
  }, [history]);

  if (authLoading) {
    return (
      <main className="page login-page">
        <section className="card login-card">
          <p className="eyebrow">Dorm Guardian</p>
          <h1>Checking access...</h1>
        </section>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <LoginScreen
        onLoginSuccess={() => {
          setAuthenticated(true);
          loadDashboardData();
        }}
      />
    );
  }

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Dorm Guardian Hardware Dashboard</p>
          <h1>Smart Room Monitor</h1>
          <p className="subtitle">
            Real STM32 sensor readings, camera streaming, motion detection,
            saved events, and rule-based alerts flowing into FastAPI, SQLite,
            and React.
          </p>
        </div>

        <div className="hero-actions">
          <div className="status-pill">
            <span
              className={health?.status === "ok" ? "dot online" : "dot offline"}
            />
            {health?.status === "ok" ? "Backend online" : "Backend offline"}
          </div>

          <button className="camera-toggle" onClick={handleLogout}>
            Logout
          </button>
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
          <h2>
            {latestReading
              ? `${formatNumber(latestReading.temperature, 1)}°C`
              : "—"}
          </h2>
          <p className="muted">
            {latestReading
              ? `Updated ${formatTime(latestReading.timestamp)}`
              : "No readings yet"}
          </p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Humidity</p>
          <h2>
            {latestReading
              ? `${formatNumber(latestReading.humidity, 1)}%`
              : "—"}
          </h2>
          <p className="muted">BME280 humidity reading</p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Pressure</p>
          <h2>
            {latestReading
              ? `${formatNumber(latestReading.pressure, 1)} hPa`
              : "—"}
          </h2>
          <p className="muted">BME280 pressure reading</p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Light</p>
          <h2>
            {latestReading
              ? `${formatNumber(latestReading.light, 1)} lux`
              : "—"}
          </h2>
          <p className="muted">BH1750 light reading</p>
        </div>
      </section>

      <section className="grid cards-grid">
        <MotionStatusCard />

        <div className="card metric-card">
          <p className="card-label">Alert System</p>
          <h2>Active</h2>
          <p className="muted">
            Rules check motion, sensors, and stale data.
          </p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Data Source</p>
          <h2>{latestReading?.source ?? "—"}</h2>
          <p className="muted">Latest hardware source</p>
        </div>

        <div className="card metric-card">
          <p className="card-label">Last Update</p>
          <h2>{latestReading ? formatTime(latestReading.timestamp) : "—"}</h2>
          <p className="muted">
            {latestReading
              ? formatDateTime(latestReading.timestamp)
              : "No readings yet"}
          </p>
        </div>
      </section>

      <CameraPanel />

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
                <Line
                  type="monotone"
                  dataKey="light"
                  name="Light lux"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <AlertsPanel />
      </section>

      <section className="grid main-grid raw-card">
        <MotionEventsPanel />

        <section className="card">
          <p className="card-label">Latest Raw Reading</p>
          <pre>{JSON.stringify(latestReading, null, 2)}</pre>
        </section>
      </section>
    </main>
  );
}

export default App;
