#!/usr/bin/env python3

import cv2
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ultralytics import YOLO


class PersonDetectorUDP(Node):
    def __init__(self):
        super().__init__("person_detector_udp")

        # ---- GStreamer RTP H.264 video input ----
        self.stream_url = (
            "udpsrc port=5000 caps=\"application/x-rtp, media=(string)video, "
            "clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96\" ! "
            "rtpjitterbuffer latency=0 drop-on-latency=true ! "
            "rtph264depay ! h264parse ! avdec_h264 ! "
            "videoconvert ! video/x-raw,format=BGR ! "
            "appsink sync=false max-buffers=1 drop=true"
        )

        self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_GSTREAMER)

        if not self.cap.isOpened():
            self.get_logger().error(
                "Could not open GStreamer stream on UDP/RTP port 5000. "
                "Make sure the Pi is sending RTP H.264 to this machine."
            )
            raise RuntimeError("GStreamer stream failed to open")
        
        # ---- YOLO model ----
        self.model = YOLO("yolov8n.pt")

        # ---- ROS publisher ----
        self.target_pub = self.create_publisher(String, "/target_person", 10)

        # ---- Tracking state ----
        self.selected_id = None
        self.detections = {}
        self.last_seen = {}

        # ---- OpenCV window ----
        self.window_name = "Person Detector - Click to select target"
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_click)

        # Timer controls processing loop
        # 0.03 sec ~= 33 FPS target. Actual FPS depends on YOLO speed.
        self.timer = self.create_timer(0.03, self.process_frame)

        self.get_logger().info("Person detector GStreamer node ready.")
        self.get_logger().info("Listening for RTP H.264 video on UDP port 5000.")
        self.get_logger().info("Click on a person in the window to select target.")

    def process_frame(self):
        success, frame = self.cap.read()

        if not success or frame is None:
            self.get_logger().warn("Dropped frame / no UDP frame available.")
            return

        # Run YOLO tracking
        results = self.model.track(
            frame,
            persist=True,
            classes=[0],      # COCO class 0 = person
            verbose=False
        )

        self.detections = {}

        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                if box.id is None:
                    continue

                track_id = int(box.id.item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                width = x2 - x1
                height = y2 - y1

                det = {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "cx": cx,
                    "cy": cy,
                    "width": width,
                    "height": height,
                }

                self.detections[track_id] = det
                self.last_seen[track_id] = det.copy()

                color = (0, 0, 255) if track_id == self.selected_id else (0, 255, 0)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"ID:{track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )

        self.publish_target(frame)

        cv2.imshow(self.window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            self.get_logger().info("Q pressed. Shutting down.")
            rclpy.shutdown()

    def mouse_click(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        for track_id, det in self.detections.items():
            if det["x1"] < x < det["x2"] and det["y1"] < y < det["y2"]:
                self.selected_id = track_id
                self.get_logger().info(f"Selected person ID: {track_id}")
                return

        self.selected_id = None
        self.get_logger().info("Target deselected")

    def publish_target(self, frame):
        if self.selected_id is None:
            return

        img_height = frame.shape[0]
        img_width = frame.shape[1]

        if self.selected_id in self.detections:
            det = self.detections[self.selected_id]
            status = "visible"
        elif self.selected_id in self.last_seen:
            det = self.last_seen[self.selected_id]
            status = "lost"
        else:
            return

        # Horizontal position still controls left/right turning
        normalized_x = (det["cx"] - img_width / 2) / (img_width / 2)

        # Distance now uses vertical size only.
        # This avoids arms making the person look "bigger" horizontally.
        normalized_size = det["height"] / img_height

        payload = {
            "id": self.selected_id,
            "status": status,
            "normalized_x": round(normalized_x, 3),
            "normalized_size": round(normalized_size, 3),
            "cx": det["cx"],
            "cy": det["cy"],
            "height": det["height"],
        }

        status_text = (
            f"Target {self.selected_id} | {status.upper()} "
            f"| x:{normalized_x:.2f} | height_size:{normalized_size:.2f}"
        )

        cv2.putText(
            frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )

        msg = String()
        msg.data = json.dumps(payload)
        self.target_pub.publish(msg)

    def destroy_node(self):
        if hasattr(self, "cap") and self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PersonDetectorUDP()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()