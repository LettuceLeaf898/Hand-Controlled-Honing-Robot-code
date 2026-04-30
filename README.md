# Hand-Controlled Honing Robot

This repository contains the main code for a wheeled robot that can be controlled in three ways:

1. **Hand-control mode** using an ESP32 glove with a BNO080 IMU.
2. **Auto-follow mode** using computer vision person detection.
3. **Manual keyboard mode** for testing and debugging.

The robot is physically driven by a Raspberry Pi. The Pi receives simple movement commands over WiFi and converts those commands into motor outputs using GPIO and PWM.

> Important: the main robot code is inside the `Code/` folder. Other folders are mostly tests, simulations, utilities, or older experiments.

---

## System Overview

The project is built around a simple command pipeline:

```text
Input source
    ↓
Command decision
    ↓
WiFi command sent to Raspberry Pi
    ↓
Raspberry Pi controls motors
    ↓
Robot moves
```

The input source can be:

- the ESP32 hand-control glove
- the person detector and auto-follow client
- the manual keyboard client

All control modes eventually send basic commands to the Raspberry Pi car server.

---

## Movement Commands

The robot uses simple single-character movement commands:

```text
F = move forward
B = move backward
L = turn left
R = turn right
S = stop
```

The Raspberry Pi receives these commands and drives the motors accordingly.

---

## Main Components

### 1. Raspberry Pi Car Controller

The Raspberry Pi is the device that actually controls the robot's motors.

It receives commands over the network and uses GPIO/PWM to control the left and right motors.

The car controller is the final layer of the system. Neither the ESP32 glove nor the person detector directly controls the motors.

General role:

```text
Receive command → interpret command → drive motors
```

---

### 2. ESP32 Hand Controller

The hand controller uses an ESP32 connected to a BNO080 IMU.

The ESP32 reads the orientation of the user's hand and converts hand movement into driving commands.

Example behavior:

```text
Tilt hand forward  → F
Tilt hand backward → B
Tilt hand left     → L
Tilt hand right    → R
Neutral position   → S
```

Main firmware file:

```text
Code/src/main.cpp
```

This file handles:

- reading the BNO080 IMU
- interpreting hand tilt
- connecting to WiFi
- sending drive commands to the Raspberry Pi
- OTA support, if enabled

The ESP32 does not drive the motors directly. It only sends commands to the Raspberry Pi.

---

### 3. Person Detection

The person detector processes camera frames and detects/tracks a person in view.

Main file:

```text
Code/person_detector.py
```

The detector produces tracking information such as:

- whether a person is visible
- the person's horizontal position in the frame
- the person's approximate size or distance
- whether the target is lost

The person detector does not directly move the robot. It provides target data that the auto-follow client uses to decide what command should be sent.

---

### 4. Auto-Follow Client

The auto-follow client receives person-tracking data and converts it into robot movement commands.

Main file:

```text
Code/auto_follow_client.py
```

Example behavior:

```text
Person centered and far away → move forward
Person too far left          → turn left
Person too far right         → turn right
Person close enough          → stop
Person lost                  → stop
```

The auto-follow client sends the final command to the Raspberry Pi car server.

---

### 5. Manual Keyboard Client

The keyboard client is used for manual testing and debugging.

Main file:

```text
Code/KeyboardDriveClient.py
```

This script lets a user drive the robot from a computer by sending commands manually over the network.

It is not required for normal robot operation.

---

## Repository Structure

```text
Code/
├── src/
│   └── main.cpp              # ESP32 glove firmware
├── person_detector.py        # Computer vision person detector
├── auto_follow_client.py     # Converts detection data into drive commands
├── KeyboardDriveClient.py    # Optional manual keyboard driving client
└── other control scripts     # Raspberry Pi car-side control code
```

Other folders, such as:

```text
Tests/
nav_sim/
glove_logic/
```

may contain experiments, simulations, older test scripts, or helper utilities. These are useful during development but are not required for basic robot operation.

---

## Control Flow

### Hand-Control Mode

```text
ESP32 glove
    ↓
BNO080 IMU reads hand orientation
    ↓
ESP32 converts tilt into F/B/L/R/S command
    ↓
Command sent over WiFi
    ↓
Raspberry Pi car server receives command
    ↓
Pi drives motors through GPIO/PWM
```

---

### Auto-Follow Mode

```text
Camera feed
    ↓
person_detector.py detects/tracks a person
    ↓
Tracking data is sent to auto_follow_client.py
    ↓
auto_follow_client.py decides F/L/R/S movement command
    ↓
Command sent to Raspberry Pi car server
    ↓
Pi drives motors through GPIO/PWM
```

---

### Manual Keyboard Mode

```text
KeyboardDriveClient.py
    ↓
User presses movement key
    ↓
Command sent over WiFi
    ↓
Raspberry Pi car server receives command
    ↓
Pi drives motors through GPIO/PWM
```

---

## Installation

### Python Environment

Create and activate a Python virtual environment.

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install opencv-python ultralytics webcolors numpy matplotlib pillow flask requests
```

#### Linux / Raspberry Pi

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python ultralytics webcolors numpy matplotlib pillow flask requests
```

Depending on the Raspberry Pi setup, GPIO control may also require:

```bash
sudo apt install python3-rpi.gpio
```

or another GPIO library compatible with the Pi OS version being used.

---

## ESP32 Requirements

The ESP32 firmware requires:

- ESP32 Arduino core
- `WiFi.h`
- `WebServer.h`
- SparkFun BNO080/BNO08x library
- ElegantOTA, if OTA updates are enabled

Main ESP32 firmware file:

```text
Code/src/main.cpp
```

Upload the firmware using PlatformIO or the Arduino IDE.

---

## Running the Robot

### 1. Start the Raspberry Pi Car Server

Run the car-side control script on the Raspberry Pi.

Example:

```bash
python3 Code/<car_server_file>.py
```

Replace `<car_server_file>` with the actual Raspberry Pi car server script used in the project.

This script should be running before the glove, auto-follow client, or keyboard client sends commands.

---

### 2. Run Hand-Control Mode

Upload the ESP32 firmware from:

```text
Code/src/main.cpp
```

Make sure the ESP32 and Raspberry Pi are on the same network or can reach each other over WiFi.

Once connected, hand gestures should send movement commands to the Raspberry Pi car server.

---

### 3. Run Auto-Follow Mode

Start the person detector:

```bash
python Code/person_detector.py
```

Then start the auto-follow client:

```bash
python Code/auto_follow_client.py
```

The person detector provides target information, and the auto-follow client decides whether the robot should move forward, turn, stop, or hold position.

---

### 4. Optional: Run Manual Keyboard Driving

Use the keyboard client when you want to manually test the robot from a PC.

```bash
python Code/KeyboardDriveClient.py --host <robot-ip> --port 5001
```

Example:

```bash
python Code/KeyboardDriveClient.py --host 10.42.0.199 --port 5001
```

---

## Important Notes

- The Raspberry Pi is responsible for physically driving the motors.
- The ESP32 glove sends commands; it does not control the motors directly.
- The person detector produces tracking data; it does not control the motors directly.
- The auto-follow client converts tracking data into movement commands.
- `KeyboardDriveClient.py` is optional and mainly used for testing.
- The `Code/` folder contains the main files needed to run the robot.
- Other folders are mostly for experiments, simulations, and development work.
- ROS may be part of the person-detection or auto-follow communication layer, but the robot's core movement system is based on sending simple commands to the Raspberry Pi car server.

---

## Summary

This project is a multi-device robot control system.

```text
Hand gestures, computer vision, or keyboard input
        ↓
Drive command decision
        ↓
WiFi command sent to Raspberry Pi
        ↓
Raspberry Pi controls the motors
        ↓
Robot moves
```

The robot can be controlled manually with the IMU glove, manually from a keyboard client, or automatically through computer vision person tracking.
