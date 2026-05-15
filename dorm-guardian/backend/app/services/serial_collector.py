import json
import sqlite3
import time
from datetime import datetime, timezone

import serial


PORT = "/dev/cu.usbmodem11403"  # Mac
# PORT = "/dev/ttyACM0"         # Raspberry Pi later

BAUD = 115200
DB_PATH = "dorm_guardian.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            light REAL,
            fan_status INTEGER NOT NULL,
            source TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_reading(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO sensor_readings (
            timestamp,
            temperature,
            humidity,
            pressure,
            light,
            fan_status,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        data.get("temperature"),
        data.get("humidity"),
        data.get("pressure"),
        data.get("light"),
        1 if data.get("fan_status") else 0,
        data.get("source", "hardware"),
    ))

    conn.commit()
    conn.close()


def main():
    init_db()

    print(f"Opening STM32 serial port: {PORT}")
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)

    print("Collecting real STM32 sensor data...\n")

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()

        if not line:
            continue

        if not line.startswith("{"):
            print("LOG:", line)
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print("BAD JSON:", line)
            continue

        if data.get("bme_status") != 0 or data.get("light_status") != 0:
            print("SKIP BAD SENSOR READ:", data)
            continue

        save_reading(data)

        print(
            f"Saved: temp={data.get('temperature')} C, "
            f"humidity={data.get('humidity')} %, "
            f"pressure={data.get('pressure')} hPa, "
            f"light={data.get('light')} lux"
        )


if __name__ == "__main__":
    main()