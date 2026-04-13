# Hand-Controlled-Honing-Robot-code

Controls a wheeled robot via hand/IMU movement and tracks a specific person using computer vision and YOLO-based clothing identification.

## Description

This project combines an ESP32 microcontroller, a Raspberry Pi, and a Python computer-vision pipeline to drive a wheeled robot. The system has two main control modes:

**IMU Hand Control (`main.cpp`):** An ESP32 reads orientation data (roll, pitch, yaw) from a BNO080 IMU sensor over I2C. When the hand tilts forward, backward, left, or right beyond a 20-degree threshold, the ESP32 sends a corresponding drive command (`F`, `B`, `L`, `R`, or `S` for stop) to the Raspberry Pi over a WiFi TCP socket. The ESP32 also hosts a small web server with an `/data` JSON endpoint and supports over-the-air (OTA) firmware updates via ElegantOTA.

**Vision-Based Person Tracking (`identify_clothes_live_app.py`):** The main live application streams video from a Raspberry Pi camera over TCP, runs YOLOv8 person detection on each frame, and identifies the dominant color of each detected person's shirt and pants regions using median/mean pixel sampling matched against CSS3 color names. Clicking on a detected person in the window starts a CSRT tracker that locks onto that individual. While tracking, the app computes a drive command based on the person's horizontal position and bounding-box size relative to the frame, then sends that command to the robot car server over TCP.

**Additional modules:**
- `KeyboardDriveClient.py` — A Tkinter GUI that sends WASD keyboard commands to the robot car server over TCP.
- `Main.py` — Test script that detects a yellow object via webcam using HSV color masking.
- `Util.py` — Utility function that computes an HSV color range (±10 hue) for a given BGR color.
- `clothesDetecttest.py` — Tests HOG-based person detection combined with a CSRT tracker on a webcam feed.
- `IdentifyClothesStaticImg.py` — Runs YOLO person detection and clothing color identification on a static image file.
- `piCameraTest.py` — Low-latency TCP video stream viewer for the Raspberry Pi camera feed.
- `NavSimuMoveTart.py` / `NavigationSimulation.py` — Turtle graphics simulations of a robot chasing a moving target.

## Installation

```
pip install opencv-python
pip install ultralytics
pip install webcolors
```

Additional Python dependencies used in the code: `numpy`, `matplotlib`, `Pillow`, `tkinter` (standard library).

The ESP32 firmware (`main.cpp`) requires the following Arduino libraries:
- `SparkFun_BNO080_Arduino_Library`
- `WiFi.h` / `WebServer.h` (ESP32 Arduino core)
- `ElegantOTA`

## Usage

**Live person tracking and robot control:**
```
python IdentifyClothesLive.py
```
Opens a window showing the camera stream with YOLO detections. Click a detected person to begin tracking. The robot will automatically steer toward the tracked person. Press `S` to stop tracking, `Q` to quit.

**Keyboard teleoperation:**
```
python KeyboardDriveClient.py --host <robot-ip> --port 5001
```
Hold W/A/S/D to drive forward/left/backward/right. Release to stop.

**Static image clothing detection:**
```
python IdentifyClothesStaticImg.py
```
Reads `people.jpg` from the working directory and prints detected shirt and pants colors to the console.

**Yellow object detection test:**
```
python Main.py
```
Opens the default webcam and draws a bounding box around any detected yellow object.


pip install opencv-python
pip install ultralytics
pip install webcolors
