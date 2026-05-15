import random
import time
from datetime import datetime

import requests

API_URL = "http://127.0.0.1:8000/api/device-ingest/sensor-reading"
DEVICE_ID = "mock-stm32-room-01"


def generate_reading() -> dict:
    """
    Generate fake room sensor readings.

    This simulates what the STM32 will eventually send:
    - temperature
    - humidity
    - air quality
    """

    hour = datetime.now().hour

    # Normal room baseline
    base_temperature = 24.5

    # Simulate warmer afternoon
    if 12 <= hour <= 17:
        base_temperature += 2.0

    temperature_c = base_temperature + random.uniform(-1.2, 1.8)

    # Occasionally simulate overheating
    if random.random() < 0.10:
        temperature_c += random.uniform(3.0, 5.0)

    humidity_percent = random.uniform(38.0, 68.0)

    # Normal air quality range
    air_quality = random.uniform(300, 900)

    # Occasionally simulate bad air quality
    if random.random() < 0.07:
        air_quality += random.uniform(1000, 2500)

    return {
        "device_id": DEVICE_ID,
        "temperature_c": round(temperature_c, 2),
        "humidity_percent": round(humidity_percent, 2),
        "air_quality": round(air_quality, 2),
    }


def send_reading(reading: dict) -> None:
    try:
        response = requests.post(API_URL, json=reading, timeout=5)

        if response.status_code == 200:
            print(f"✅ Sent: {reading}")
        else:
            print(f"❌ Rejected: {response.status_code} {response.text}")

    except requests.RequestException as error:
        print(f"❌ Could not reach backend: {error}")


def main() -> None:
    print("Starting Dorm Guardian mock sensor sender...")
    print(f"Sending fake readings to: {API_URL}")
    print("Press CTRL+C to stop.\n")

    while True:
        reading = generate_reading()
        send_reading(reading)
        time.sleep(5)


if __name__ == "__main__":
    main()