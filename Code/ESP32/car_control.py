import requests
import time

try:
    import RPi.GPIO as GPIO
    IS_MOCK_GPIO = False
except ModuleNotFoundError:
    IS_MOCK_GPIO = True

    class _MockPWM:
        def __init__(self, pin, freq):
            self.pin = pin
            self.freq = freq
            self.duty = 0

        def start(self, duty):
            self.duty = duty
            print(f"[MOCK GPIO] PWM pin={self.pin} freq={self.freq} start duty={duty}")

        def ChangeDutyCycle(self, duty):
            self.duty = duty

    class _MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0

        def setmode(self, mode):
            print(f"[MOCK GPIO] setmode({mode})")

        def setup(self, pin, mode):
            print(f"[MOCK GPIO] setup(pin={pin}, mode={mode})")

        def PWM(self, pin, freq):
            return _MockPWM(pin, freq)

        def output(self, pin, value):
            pass

        def cleanup(self):
            print("[MOCK GPIO] cleanup()")

    GPIO = _MockGPIO()

# --- ESP32 ---
ESP32_IP = "192.168.x.x"  # replace with your ESP32's IP
url = f"http://{ESP32_IP}/data"

# --- TB6612FNG Pin Setup ---
# Change these to whatever GPIO pins you wire up
AIN1 = 17
AIN2 = 27
PWMA = 18  # left motor
BIN1 = 22
BIN2 = 23
PWMB = 24  # right motor
STBY = 25  # standby pin, must be HIGH to enable motors

GPIO.setmode(GPIO.BCM)
for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    GPIO.setup(pin, GPIO.OUT)

pwm_a = GPIO.PWM(PWMA, 1000)
pwm_b = GPIO.PWM(PWMB, 1000)
pwm_a.start(0)
pwm_b.start(0)

GPIO.output(STBY, GPIO.HIGH)  # take out of standby

if IS_MOCK_GPIO:
    print("Running with MOCK GPIO (Windows/non-RPi). No real motor signals will be sent.")

def move(left_speed, left_fwd, right_speed, right_fwd):
    GPIO.output(AIN1, GPIO.HIGH if left_fwd else GPIO.LOW)
    GPIO.output(AIN2, GPIO.LOW if left_fwd else GPIO.HIGH)
    GPIO.output(BIN1, GPIO.HIGH if right_fwd else GPIO.LOW)
    GPIO.output(BIN2, GPIO.LOW if right_fwd else GPIO.HIGH)
    pwm_a.ChangeDutyCycle(left_speed)
    pwm_b.ChangeDutyCycle(right_speed)

def stop():
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)

# --- Main Loop ---
try:
    while True:
        try:
            r = requests.get(url, timeout=1)
            data = r.json()
            pitch = data['pitch']
            roll  = data['roll']

            if pitch > 20:        # tilt forward → forward
                move(70, True, 70, True)
            elif pitch < -20:     # tilt back → reverse
                move(70, False, 70, False)
            elif roll > 20:       # tilt right → turn right
                move(70, True, 30, True)
            elif roll < -20:      # tilt left → turn left
                move(30, True, 70, True)
            else:                 # neutral → stop
                stop()

        except Exception as e:
            print("Error:", e)
            stop()

        time.sleep(0.05)

except KeyboardInterrupt:
    stop()
    GPIO.cleanup()
