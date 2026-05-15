# Dorm Guardian Web App

This folder contains the backend and frontend application for the Dorm Guardian project.

The STM32 firmware is kept separately in:

```text
../dorm_guardian_stm32/
```

## What this app does

The web app receives real hardware sensor data, stores it locally, exposes API endpoints, streams camera video, runs motion detection, saves motion events, generates rule-based alerts, and displays everything in a React dashboard.

## Folder structure

```text
dorm-guardian/
  backend/
    app/
      main.py
      services/
        serial_collector.py
    requirements.txt
    dorm_guardian.db       # local only, not committed

  frontend/
    src/
      App.tsx
      App.css
    package.json
```

## Backend

The backend uses:

- FastAPI
- SQLite
- OpenCV
- Python serial reading

Main responsibilities:

- read sensor data from SQLite
- expose latest and historical sensor readings
- stream camera frames
- run OpenCV motion detection
- save motion events
- generate rule-based alerts
- expose API endpoints for the React dashboard

## Backend setup

From this folder:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run backend:

```bash
python -m uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Serial collector

The serial collector reads newline-delimited JSON from the STM32 over USB serial and writes the data into SQLite.

Run it in a separate terminal:

```bash
cd backend
source venv/bin/activate
python -m app.services.serial_collector
```

Expected STM32 JSON format:

```json
{
  "device_id": "nucleo-f103rb-01",
  "temperature": 24.95,
  "humidity": 58.37,
  "pressure": 1000.06,
  "light": 86.66,
  "fan_status": false,
  "source": "hardware"
}
```

## Frontend

The frontend uses:

- React
- TypeScript
- Vite
- Recharts

Main dashboard features:

- live temperature card
- live humidity card
- live pressure card
- live light card
- sensor history chart
- camera preview
- motion detection stream
- live motion status
- saved motion events
- recent alerts
- latest raw sensor reading

## Frontend setup

From this folder:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## API endpoints

Health:

```text
GET /api/health
```

Sensors:

```text
GET /api/sensors/latest
GET /api/sensors/history?limit=40
```

Camera:

```text
GET /api/camera/status
GET /api/camera/stream
GET /api/camera/motion-stream
GET /api/camera/motion-status
```

Motion:

```text
GET /api/motion/events
GET /api/motion/summary
```

Alerts:

```text
GET /api/alerts
GET /api/alerts/summary
```

## Running the full local system

Use three terminals.

Terminal 1 — serial collector:

```bash
cd dorm-guardian/backend
source venv/bin/activate
python -m app.services.serial_collector
```

Terminal 2 — backend:

```bash
cd dorm-guardian/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

Terminal 3 — frontend:

```bash
cd dorm-guardian/frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Privacy behavior

The current prototype streams the camera locally through FastAPI.

The app does not save video or images. It only stores metadata:

- sensor readings
- motion event timestamp
- motion area
- alert type
- alert severity
- alert message
- alert source

The local SQLite database is ignored by Git.

## Current limitations

- Camera source selection on macOS can be affected by iPhone Continuity Camera.
- Fan automation is paused until a safe replacement driver is used.
- Raspberry Pi deployment is not completed yet.
- Authentication is not implemented yet.
- Camera and backend are currently local-development only.

## Planned next steps

- Raspberry Pi deployment
- local network dashboard access
- auto-start backend service on boot
- improved camera configuration
- person detection
- servo tracking
- safe fan control with a new driver
- authentication
- security hardening
- improved alert configuration

## Notes

This folder is only the web application part of the project.

The full project also includes embedded STM32 firmware in:

```text
../dorm_guardian_stm32/
```