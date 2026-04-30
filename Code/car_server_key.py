# Code run on the car
import RPi.GPIO as GPIO
import socket
import time

# LEFT
L_IN1 = 17
L_IN2 = 27
L_PWM = 22

# RIGHT
R_IN1 = 23
R_IN2 = 24
R_PWM = 25

# STBY
L_STBY = 5
R_STBY = 6

cam = False
LAPTOP_IP = "172.20.10.7"

GPIO.setmode(GPIO.BCM)

GPIO.setup([L_IN1, L_IN2, R_IN1, R_IN2], GPIO.OUT)
GPIO.setup(L_PWM, GPIO.OUT)
GPIO.setup(R_PWM, GPIO.OUT)
GPIO.setup(L_STBY, GPIO.OUT)
GPIO.setup(R_STBY, GPIO.OUT)

GPIO.output(L_STBY, 1)
GPIO.output(R_STBY, 1)

left_pwm = GPIO.PWM(L_PWM, 1000)
right_pwm = GPIO.PWM(R_PWM, 1000)

left_pwm.start(0)
right_pwm.start(0)

def set_motor(in1, in2, pwm, speed):
    speed = max(-100, min(100, speed))

    if speed > 0:
        GPIO.output(in1, 1)
        GPIO.output(in2, 0)
    elif speed < 0:
        GPIO.output(in1, 0)
        GPIO.output(in2, 1)
    else:
        GPIO.output(in1, 0)
        GPIO.output(in2, 0)

    pwm.ChangeDutyCycle(abs(speed))

def forward(speed=70):
    set_motor(L_IN1, L_IN2, left_pwm, speed)
    set_motor(R_IN1, R_IN2, right_pwm, speed)

def backward(speed=70):
    set_motor(L_IN1, L_IN2, left_pwm, -speed)
    set_motor(R_IN1, R_IN2, right_pwm, -speed)

def left(speed=70):
    set_motor(L_IN1, L_IN2, left_pwm, -speed)
    set_motor(R_IN1, R_IN2, right_pwm, speed)

def right(speed=70):
    set_motor(L_IN1, L_IN2, left_pwm, speed)
    set_motor(R_IN1, R_IN2, right_pwm, -speed)

def stop():
    set_motor(L_IN1, L_IN2, left_pwm, 0)
    set_motor(R_IN1, R_IN2, right_pwm, 0)

def cleanup():
    stop()
    left_pwm.stop()
    right_pwm.stop()
    GPIO.output(L_STBY, 0)
    GPIO.output(R_STBY, 0)
    GPIO.cleanup()

HOST = "0.0.0.0"
PORT = 5001
TIMEOUT_SECONDS = 0.5

def handle_command(cmd: str, cam: bool):
    cmd = cmd.strip().upper()

    if cmd == "F":
        forward()
    elif cmd == "B":
        backward()
    elif cmd == "L":
        left()
    elif cmd == "R":
        right()
    elif cmd == "S":
        stop()
    elif cmd == "C":
        cam = True if not cam else False
    else:
        print("Unknown command:", cmd)

def main():
    cam = False
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    print(f"Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()

            if cam == True and addr[0] == str(LAPTOP_IP):
                print(f"addr: {addr[0]} | ignore_ip: {LAPTOP_IP}")
                continue

            print("Connected by", addr)

            conn.settimeout(0.1)
            last_msg_time = time.time()
            buffer = b""

            try:
                while True:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break

                        buffer += data
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            cmd = line.decode("utf-8", errors="ignore")
                            print("CMD:", cmd.strip())
                            handle_command(cmd, cam)
                            last_msg_time = time.time()

                    except socket.timeout:
                        if time.time() - last_msg_time > TIMEOUT_SECONDS:
                            stop()

            finally:
                stop()
                conn.close()

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        cleanup()
        server.close()

if __name__ == "__main__":
    main()