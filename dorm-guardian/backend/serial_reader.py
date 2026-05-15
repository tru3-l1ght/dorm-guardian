import json
import time
import serial

PORT = "/dev/cu.usbmodem11403"   # Mac
# PORT = "/dev/ttyACM0"          # Raspberry Pi later

BAUD = 115200

def main():
    print(f"Opening serial port: {PORT}")

    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)

    print("Reading STM32 JSON...\n")

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

        print(data)

if __name__ == "__main__":
    main()