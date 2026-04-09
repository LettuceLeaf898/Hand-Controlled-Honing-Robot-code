import os
import socket
import sys
import time

import cv2
import numpy as np
import webcolors
from ultralytics import YOLO


WINDOW_NAME = "Live AI Detection"


def get_color_name(rgb_triplet):
    try:
        return webcolors.rgb_to_name(rgb_triplet)
    except ValueError:
        min_dist = float("inf")
        closest_name = "unknown"

        for name in webcolors.names("css3"):
            standard_rgb = webcolors.name_to_rgb(name)
            dist = (
                (standard_rgb.red - rgb_triplet[0]) ** 2
                + (standard_rgb.green - rgb_triplet[1]) ** 2
                + (standard_rgb.blue - rgb_triplet[2]) ** 2
            )

            if dist < min_dist:
                min_dist = dist
                closest_name = name

        return closest_name


def get_dominant_color(image_roi):
    if image_roi.size == 0:
        return (0, 0, 0)

    h, w, _ = image_roi.shape
    margin_h, margin_w = int(h * 0.2), int(w * 0.2)
    center_roi = image_roi[margin_h : h - margin_h, margin_w : w - margin_w]

    if center_roi.size == 0:
        return (0, 0, 0)

    pixels = center_roi.reshape(-1, 3)
    return tuple(np.mean(pixels, axis=0).astype(int))


def apply_clahe(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


def create_tracker():
    legacy = getattr(cv2, "legacy", None)
    if legacy is not None:
        tracker_factory = getattr(legacy, "TrackerCSRT_create", None)
        if tracker_factory is not None:
            return tracker_factory()

    tracker_factory = getattr(cv2, "TrackerCSRT_create", None)
    if tracker_factory is not None:
        return tracker_factory()

    raise RuntimeError(
        "No compatible OpenCV tracker available. Install opencv-contrib-python if you need tracking support."
    )


def extract_host_from_stream_url(stream_url):
    raw = stream_url.split("://", 1)[-1]
    raw = raw.split("?", 1)[0]
    if ":" in raw:
        host, _port = raw.rsplit(":", 1)
        return host
    return raw


class LiveClothesTrackerApp:
    def __init__(
        self,
        stream_url="tcp://10.25.68.108:5000",
        model_path="yolov8n.pt",
        car_host=None,
        car_port=5001,
    ):
        self.stream_url = stream_url
        self.model = YOLO(model_path)
        self.car_host = car_host or extract_host_from_stream_url(stream_url)
        self.car_port = car_port
        self.zone_area = [100, 100, 500, 450]
        self.latest_detections = []
        self.latest_frame = None
        self.tracker = None
        self.tracking_label = None
        self.tracking_box = None
        self.tracking_active = False
        self.car_socket = None
        self.last_sent_command = None
        self.last_connect_attempt = 0.0

    def open_low_latency_capture(self):
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            "fflags;nobuffer|flags;low_delay|avioflags;direct|probesize;32|analyzeduration;0",
        )

        cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.stream_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def read_latest_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return ret, frame

        for _ in range(2):
            if not cap.grab():
                break
            next_ret, next_frame = cap.retrieve()
            if not next_ret:
                break
            frame = next_frame

        return True, frame

    def stop_tracking(self):
        self.tracker = None
        self.tracking_label = None
        self.tracking_box = None
        self.tracking_active = False

    def connect_car_server(self):
        if self.car_socket is not None:
            return True

        now = time.time()
        if now - self.last_connect_attempt < 1.0:
            return False

        self.last_connect_attempt = now
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)

        try:
            sock.connect((self.car_host, self.car_port))
            self.car_socket = sock
            print(f"Connected to car server at {self.car_host}:{self.car_port}")
            return True
        except OSError:
            sock.close()
            return False

    def close_car_socket(self):
        if self.car_socket is not None:
            try:
                self.car_socket.close()
            finally:
                self.car_socket = None

    def send_car_command(self, cmd):
        cmd = cmd.strip().upper()
        if not cmd or cmd == self.last_sent_command:
            return

        if not self.connect_car_server():
            return

        sock = self.car_socket
        if sock is None:
            return

        try:
            sock.sendall(f"{cmd}\n".encode("utf-8"))
            self.last_sent_command = cmd
        except OSError:
            self.close_car_socket()

    def get_drive_command(self, frame_shape, bbox):
        frame_h, frame_w = frame_shape[:2]
        x1, y1, x2, y2 = bbox

        center_x = (x1 + x2) / 2
        offset = center_x - (frame_w / 2)
        turn_tolerance = frame_w * 0.12

        box_area = max(1, (x2 - x1) * (y2 - y1))
        frame_area = max(1, frame_w * frame_h)
        size_ratio = box_area / frame_area

        if offset < -turn_tolerance:
            return "L"
        if offset > turn_tolerance:
            return "R"
        if size_ratio < 0.10:
            return "F"
        if size_ratio > 0.30:
            return "B"
        return "S"

    def start_tracking(self, frame, bbox, label):
        try:
            self.tracker = create_tracker()
        except RuntimeError as error:
            print(str(error), file=sys.stderr)
            self.stop_tracking()
            return

        self.tracker.init(frame, bbox)
        self.tracking_label = label
        self.tracking_box = bbox
        self.tracking_active = True

    def on_mouse(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        for detection in self.latest_detections:
            x1, y1, x2, y2 = detection["bbox"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                if self.latest_frame is not None:
                    self.start_tracking(self.latest_frame, detection["bbox"], detection["label"])
                return

    def identify_clothing(self, frame):
        results = self.model(frame, verbose=False)[0]
        h, w, _ = frame.shape
        margin = 5
        full_body_count = 0
        detections = []

        for box in results.boxes:
            if int(box.cls.item()) != 0:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            is_full_body = x1 > margin and y1 > margin and x2 < (w - margin) and y2 < (h - margin)

            if is_full_body:
                full_body_count += 1
                box_color = (0, 255, 0)
                status_text = "Full Body"
            else:
                box_color = (0, 0, 255)
                status_text = "Partial"

            y1_c, y2_c = max(0, y1), min(h, y2)
            x1_c, x2_c = max(0, x1), min(w, x2)
            person_height = y2_c - y1_c
            head_gap = int(person_height * 0.2)

            shirt_roi = frame[y1_c + head_gap : y1_c + head_gap + person_height // 3, x1_c:x2_c]
            pants_roi = frame[y1_c + head_gap + person_height // 2 : y2_c, x1_c:x2_c]

            s_name = get_color_name(get_dominant_color(shirt_roi)[::-1])
            p_name = get_color_name(get_dominant_color(pants_roi)[::-1])

            detections.append(
                {
                    "bbox": (x1, y1, x2, y2),
                    "label": f"{status_text} | S: {s_name} | P: {p_name}",
                    "color": box_color,
                }
            )

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(
                frame,
                f"{status_text} | S: {s_name}",
                (x1, y1 - 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                box_color,
                2,
            )
            cv2.putText(
                frame,
                f"P: {p_name}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                box_color,
                2,
            )

        self.latest_detections = detections
        return frame, full_body_count

    def get_follow_direction(self, frame_width, bbox):
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        offset = center_x - (frame_width / 2)
        tolerance = frame_width * 0.10

        if abs(offset) <= tolerance:
            return "center"
        if offset < 0:
            return "move left"
        return "move right"

    def run(self):
        cap = self.open_low_latency_capture()
        if not cap.isOpened():
            print(f"Error: could not open stream {self.stream_url}", file=sys.stderr)
            raise SystemExit(1)

        print(f"Car command target: {self.car_host}:{self.car_port}")

        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self.on_mouse)

        while True:
            ret, frame = self.read_latest_frame(cap)
            if not ret:
                break

            self.latest_frame = frame
            processed_frame, count = self.identify_clothing(frame)

            if self.tracking_active and self.tracker is not None:
                success, box = self.tracker.update(frame)
                if success:
                    x, y, w, h = [int(v) for v in box]
                    self.tracking_box = (x, y, x + w, y + h)
                    drive_cmd = self.get_drive_command(processed_frame.shape, self.tracking_box)
                    self.send_car_command(drive_cmd)
                    cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 165, 255), 3)
                    cv2.putText(
                        processed_frame,
                        f"Tracking: {self.tracking_label}",
                        (x, y - 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),
                        2,
                    )
                    follow_hint = self.get_follow_direction(processed_frame.shape[1], self.tracking_box)
                    cv2.putText(
                        processed_frame,
                        f"Follow: {follow_hint}",
                        (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),
                        2,
                    )
                    cv2.putText(
                        processed_frame,
                        f"Car CMD: {drive_cmd}",
                        (x, y - 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),
                        2,
                    )
                else:
                    self.stop_tracking()
                    self.send_car_command("S")
                    cv2.putText(
                        processed_frame,
                        "Tracking lost",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
            else:
                self.send_car_command("S")

            cv2.rectangle(
                processed_frame,
                (self.zone_area[0], self.zone_area[1]),
                (self.zone_area[2], self.zone_area[3]),
                (255, 255, 0),
                2,
            )
            cv2.rectangle(processed_frame, (10, 10), (220, 50), (0, 0, 0), -1)
            cv2.putText(
                processed_frame,
                f"People in ROI: {count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                processed_frame,
                "Click target to track | S to stop",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            cv2.imshow(WINDOW_NAME, processed_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key in (ord("s"), ord("S")):
                self.stop_tracking()
                self.send_car_command("S")

        self.send_car_command("S")
        self.close_car_socket()
        cap.release()
        cv2.destroyAllWindows()


def main():
    app = LiveClothesTrackerApp()
    app.run()
