import cv2
import socket
import threading
import queue
import time
from ultralytics import YOLO

STREAM_PIPELINE = (
    "udpsrc port=5000 ! "
    "application/x-rtp, encoding-name=H264 ! "
    "rtph264depay ! decodebin ! videoconvert ! "
    "appsink max-buffers=1 drop=true"
)

CAR_IP = "10.139.21.100"    
CAR_PORT = 5000

frame_queue = queue.Queue(maxsize=1)
result_queue = queue.Queue(maxsize=1)

RUN_YOLO_EVERY = 3  # 🔥 HUGE optimization


# =========================
# THREAD 1: CAPTURE (NO BUFFER)
# =========================
def capture_thread():
    cap = cv2.VideoCapture(STREAM_PIPELINE, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Stream failed")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        if frame_queue.full():
            frame_queue.get()

        frame_queue.put(frame)


# =========================
# THREAD 2: YOLO (N-FRAMES)
# =========================
def yolo_thread():
    model = YOLO("yolov8n.pt")

    frame_count = 0
    last_box = None

    while True:
        frame = frame_queue.get()
        frame_count += 1

        # 🔥 RUN YOLO ONLY EVERY N FRAMES
        if frame_count % RUN_YOLO_EVERY == 0:
            results = model(frame, verbose=False)[0]

            last_box = None
            for box in results.boxes:
                if int(box.cls.item()) == 0:
                    last_box = list(map(int, box.xyxy[0]))
                    break

        # push latest result ALWAYS
        if result_queue.full():
            result_queue.get()

        result_queue.put((frame, last_box))


# =========================
# THREAD 3: CONTROL (FAST)
# =========================
def control_thread():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((CAR_IP, CAR_PORT))

    last_cmd = None

    while True:
        frame, box = result_queue.get()

        cmd = "S"

        if box:
            x1, y1, x2, y2 = box
            center = (x1 + x2) // 2
            width = frame.shape[1]

            if center < width * 0.4:
                cmd = "L"
            elif center > width * 0.6:
                cmd = "R"
            else:
                cmd = "F"

        if cmd != last_cmd:
            sock.sendall((cmd + "\n").encode())
            last_cmd = cmd


# =========================
# DISPLAY LOOP (OPTIONAL)
# =========================
def display():
    while True:
        if result_queue.empty():
            continue

        frame, box = result_queue.get()

        if box:
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)

        cv2.imshow("LOW LATENCY", frame)

        if cv2.waitKey(1) == ord("q"):
            break


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=capture_thread, daemon=True).start()
    threading.Thread(target=yolo_thread, daemon=True).start()
    threading.Thread(target=control_thread, daemon=True).start()

    display()