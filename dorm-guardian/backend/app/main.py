import sqlite3
import time
from datetime import datetime
from typing import Generator

import cv2
import os

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except Exception:
    Picamera2 = None
    PICAMERA2_AVAILABLE = False
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

DB_PATH = "dorm_guardian.db"

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_ENABLED = os.getenv("CAMERA_ENABLED", "true").lower() in ["1", "true", "yes"]
USE_PICAMERA2 = os.getenv("USE_PICAMERA2", "auto").lower()

MOTION_SAVE_COOLDOWN_SECONDS = 10
ALERT_SAVE_COOLDOWN_SECONDS = 30

TEMP_HIGH_C = 28.0
TEMP_LOW_C = 15.0
HUMIDITY_HIGH = 70.0
HUMIDITY_LOW = 30.0
LIGHT_HIGH_LUX = 800.0
SENSOR_STALE_SECONDS = 15

last_motion_state = {
    "motion_detected": False,
    "last_motion_time": None,
    "motion_area": 0,
}

last_saved_motion_time = 0.0
last_alert_times: dict[str, float] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
	"http://192.168.1.182:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS motion_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            motion_area INTEGER NOT NULL,
            source TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


def save_alert(
    alert_type: str,
    severity: str,
    message: str,
    source: str,
    cooldown_seconds: int = ALERT_SAVE_COOLDOWN_SECONDS,
):
    now = time.time()
    last_time = last_alert_times.get(alert_type, 0.0)

    if now - last_time < cooldown_seconds:
        return

    last_alert_times[alert_type] = now

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO alerts (
            timestamp,
            type,
            severity,
            message,
            source
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        now_iso(),
        alert_type,
        severity,
        message,
        source,
    ))

    conn.commit()
    conn.close()


def evaluate_sensor_alerts(reading: sqlite3.Row | None):
    if reading is None:
        return

    timestamp = reading["timestamp"]
    temperature = reading["temperature"]
    humidity = reading["humidity"]
    light = reading["light"]

    try:
        reading_time = datetime.fromisoformat(timestamp)
        age_seconds = (datetime.now() - reading_time).total_seconds()

        if age_seconds > SENSOR_STALE_SECONDS:
            save_alert(
                "sensor_stale",
                "warning",
                f"Sensor data is stale: last update was {int(age_seconds)} seconds ago.",
                "system",
            )
    except Exception:
        pass

    if temperature is not None and temperature >= TEMP_HIGH_C:
        save_alert(
            "temperature_high",
            "warning",
            f"Temperature is high: {temperature:.1f}°C.",
            "bme280",
        )

    if temperature is not None and temperature <= TEMP_LOW_C:
        save_alert(
            "temperature_low",
            "info",
            f"Temperature is low: {temperature:.1f}°C.",
            "bme280",
        )

    if humidity is not None and humidity >= HUMIDITY_HIGH:
        save_alert(
            "humidity_high",
            "warning",
            f"Humidity is high: {humidity:.1f}%.",
            "bme280",
        )

    if humidity is not None and humidity <= HUMIDITY_LOW:
        save_alert(
            "humidity_low",
            "info",
            f"Humidity is low: {humidity:.1f}%.",
            "bme280",
        )

    if light is not None and light >= LIGHT_HIGH_LUX:
        save_alert(
            "light_high",
            "info",
            f"Room light level is high: {light:.1f} lux.",
            "bh1750",
        )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "dorm-guardian-backend",
    }


@app.get("/api/sensors/latest")
def get_latest_sensor_reading():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            timestamp,
            temperature,
            humidity,
            pressure,
            light,
            fan_status,
            source
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if row is None:
        return {"status": "no_data"}

    evaluate_sensor_alerts(row)

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "pressure": row["pressure"],
        "light": row["light"],
        "fan_status": bool(row["fan_status"]),
        "source": row["source"],
    }


@app.get("/api/sensors/history")
def get_sensor_history(limit: int = 50):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            timestamp,
            temperature,
            humidity,
            pressure,
            light,
            fan_status,
            source
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "pressure": row["pressure"],
            "light": row["light"],
            "fan_status": bool(row["fan_status"]),
            "source": row["source"],
        }
        for row in rows
    ]


def save_motion_event(motion_area: int):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO motion_events (
            timestamp,
            motion_area,
            source
        )
        VALUES (?, ?, ?)
    """, (
        now_iso(),
        motion_area,
        "camera",
    ))

    conn.commit()
    conn.close()

    save_alert(
        "motion_detected",
        "warning",
        f"Motion detected in room. Motion area: {motion_area}.",
        "camera",
    )


@app.get("/api/motion/events")
def get_motion_events(limit: int = 20):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            timestamp,
            motion_area,
            source
        FROM motion_events
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "motion_area": row["motion_area"],
            "source": row["source"],
        }
        for row in rows
    ]


@app.get("/api/motion/summary")
def get_motion_summary():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS count_today
        FROM motion_events
        WHERE DATE(timestamp) = DATE('now', 'localtime')
    """)
    count_row = cur.fetchone()

    cur.execute("""
        SELECT
            id,
            timestamp,
            motion_area,
            source
        FROM motion_events
        ORDER BY id DESC
        LIMIT 1
    """)
    latest_row = cur.fetchone()

    conn.close()

    latest_event = None

    if latest_row is not None:
        latest_event = {
            "id": latest_row["id"],
            "timestamp": latest_row["timestamp"],
            "motion_area": latest_row["motion_area"],
            "source": latest_row["source"],
        }

    return {
        "count_today": count_row["count_today"] if count_row else 0,
        "latest_event": latest_event,
    }


@app.get("/api/alerts")
def get_alerts(limit: int = 20):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            timestamp,
            type,
            severity,
            message,
            source
        FROM alerts
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "type": row["type"],
            "severity": row["severity"],
            "message": row["message"],
            "source": row["source"],
        }
        for row in rows
    ]


@app.get("/api/alerts/summary")
def get_alerts_summary():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS count_today
        FROM alerts
        WHERE DATE(timestamp) = DATE('now', 'localtime')
    """)
    count_row = cur.fetchone()

    cur.execute("""
        SELECT COUNT(*) AS warning_count
        FROM alerts
        WHERE severity = 'warning'
          AND DATE(timestamp) = DATE('now', 'localtime')
    """)
    warning_row = cur.fetchone()

    cur.execute("""
        SELECT
            id,
            timestamp,
            type,
            severity,
            message,
            source
        FROM alerts
        ORDER BY id DESC
        LIMIT 1
    """)
    latest_row = cur.fetchone()

    conn.close()

    latest_alert = None

    if latest_row is not None:
        latest_alert = {
            "id": latest_row["id"],
            "timestamp": latest_row["timestamp"],
            "type": latest_row["type"],
            "severity": latest_row["severity"],
            "message": latest_row["message"],
            "source": latest_row["source"],
        }

    return {
        "count_today": count_row["count_today"] if count_row else 0,
        "warning_count_today": warning_row["warning_count"] if warning_row else 0,
        "latest_alert": latest_alert,
    }

class PiCameraWrapper:
    def __init__(self):
        if not PICAMERA2_AVAILABLE or Picamera2 is None:
            raise RuntimeError("Picamera2 is not available.")

        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={
                "size": (640, 480),
                "format": "RGB888",
            }
        )
        self.camera.configure(config)
        self.camera.start()
        time.sleep(1.0)

    def read(self):
        frame = self.camera.capture_array()
        return True, frame

    def release(self):
        # Important:
        # Do not stop the Pi camera after every stream request.
        # The Raspberry Pi camera stack can lock if we rapidly open/close it.
        pass

    def shutdown(self):
        try:
            self.camera.stop()
            self.camera.close()
        except Exception:
            pass
shared_camera = None


def get_shared_camera():
    global shared_camera

    if shared_camera is not None:
        return shared_camera

    if USE_PICAMERA2 in ["1", "true", "yes", "auto"] and PICAMERA2_AVAILABLE:
        try:
            print("Opening shared Raspberry Pi Camera with Picamera2")
            shared_camera = PiCameraWrapper()
            return shared_camera
        except Exception as exc:
            print(f"Shared Picamera2 failed: {exc}")

            if USE_PICAMERA2 != "auto":
                return None

    print(f"Opening OpenCV camera index {CAMERA_INDEX}")
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        return None

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)

    shared_camera = camera
    return shared_camera

def open_camera():
    return get_shared_camera()

def encode_frame(frame) -> bytes | None:
    ret, buffer = cv2.imencode(".jpg", frame)

    if not ret:
        return None

    return buffer.tobytes()


def mjpeg_chunk(frame_bytes: bytes) -> bytes:
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n" +
        frame_bytes +
        b"\r\n"
    )


def generate_camera_frames() -> Generator[bytes, None, None]:
    if not CAMERA_ENABLED:
        return

    camera = open_camera()

    if camera is None:
        print("ERROR: Could not open camera.")
        return

    while True:
        success, frame = camera.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)

        frame_bytes = encode_frame(frame)

        if frame_bytes is None:
            continue

        yield mjpeg_chunk(frame_bytes)

def generate_motion_frames() -> Generator[bytes, None, None]:
    global last_saved_motion_time

    if not CAMERA_ENABLED:
        return

    camera = open_camera()

    if camera is None:
        print("ERROR: Could not open camera.")
        return

    previous_gray = None

    while True:
        success, frame = camera.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        motion_detected = False
        total_motion_area = 0

        if previous_gray is not None:
            delta = cv2.absdiff(previous_gray, gray)
            threshold = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            threshold = cv2.dilate(threshold, None, iterations=2)

            contours, _ = cv2.findContours(
                threshold,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            for contour in contours:
                area = cv2.contourArea(contour)

                if area < 1200:
                    continue

                motion_detected = True
                total_motion_area += int(area)

                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        previous_gray = gray
        current_time = time.time()

        if motion_detected:
            timestamp = now_iso()

            last_motion_state["motion_detected"] = True
            last_motion_state["last_motion_time"] = timestamp
            last_motion_state["motion_area"] = total_motion_area

            if current_time - last_saved_motion_time >= MOTION_SAVE_COOLDOWN_SECONDS:
                save_motion_event(total_motion_area)
                last_saved_motion_time = current_time

            label = f"MOTION DETECTED area={total_motion_area}"
            color = (0, 255, 0)
        else:
            last_motion_state["motion_detected"] = False
            last_motion_state["motion_area"] = 0

            label = "No motion"
            color = (180, 180, 180)

        cv2.putText(
            frame,
            label,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2,
            cv2.LINE_AA,
        )

        frame_bytes = encode_frame(frame)

        if frame_bytes is None:
            continue

        yield mjpeg_chunk(frame_bytes)

@app.get("/api/camera/stream")
def camera_stream():
    if not CAMERA_ENABLED:
        return {
            "status": "disabled",
            "reason": "Camera is disabled for privacy.",
        }

    return StreamingResponse(
        generate_camera_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/camera/motion-stream")
def motion_stream():
    if not CAMERA_ENABLED:
        return {
            "status": "disabled",
            "reason": "Camera is disabled for privacy.",
        }

    return StreamingResponse(
        generate_motion_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@app.get("/api/camera/status")
def camera_status():
    return {
        "camera_index": CAMERA_INDEX,
        "enabled": CAMERA_ENABLED,
        "available": True,
        "backend": "picamera2" if PICAMERA2_AVAILABLE else "opencv",
        "picamera2_available": PICAMERA2_AVAILABLE,
        "use_picamera2": USE_PICAMERA2,
        "note": "Status endpoint does not open the camera to avoid Pi camera locking.",
    }

@app.get("/api/camera/motion-status")
def motion_status():
    return last_motion_state
