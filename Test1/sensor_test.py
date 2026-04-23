import requests
import time
import sys

ESP32_IP = "10.42.0.2"  # <-- update to your ESP32's IP from Serial Monitor
url = f"http://{ESP32_IP}/data"

print(f"Connecting to ESP32 at {url} ...")
print("Press Ctrl+C to stop\n")

while True:
    try:
        r = requests.get(url, timeout=2)
        data = r.json()
        roll  = data['roll']
        pitch = data['pitch']
        yaw   = data['yaw']
        print(f"Roll: {roll:>8.2f}  Pitch: {pitch:>8.2f}  Yaw: {yaw:>8.2f}", end="\r")
    except requests.exceptions.ConnectTimeout:
        print(f"Timeout — can't reach {ESP32_IP}. Are you on the same network?")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Connection refused — wrong IP or ESP32 not running?")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
    time.sleep(0.1)
