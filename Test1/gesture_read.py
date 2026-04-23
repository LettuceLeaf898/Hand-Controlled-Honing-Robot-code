import requests
import time

url = "http://10.42.0.1/data"  # replace with your ESP32's IP from Serial Monitor

def get_command(pitch, roll):
    if pitch > 20:
        return "F"
    elif pitch < -20:
        return "B"
    elif roll > 20:
        return "R"
    elif roll < -20:
        return "L"
    else:
        return "S"

while True:
    try:
        r = requests.get(url, timeout=1)
        data = r.json()
        pitch = data['pitch']
        roll  = data['roll']
        cmd = get_command(pitch, roll)
        print(f"Roll: {roll:.1f}  Pitch: {pitch:.1f}  Command: {cmd}")
    except Exception as e:
        print("Error:", e)
    time.sleep(0.05)
