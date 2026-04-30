#!/usr/bin/env python3
"""
person_detector.py
------------------
ROS2 node that:
  - Subscribes to /image_raw (camera feed)
  - Detects and tracks people using YOLOv8
  - Displays bounding boxes + tracking IDs
  - Lets user click a person to select as navigation target
  - Publishes target info to /target_person
  - If target is lost, publishes last known position with status 'lost'

Published Topics:
  /target_person  (std_msgs/String)  JSON payload with target info

Subscribed Topics:
  /image_raw  (sensor_msgs/Image)  Camera feed

Requirements:
  pip install ultralytics opencv-python --break-system-packages
  sudo apt install ros-jazzy-cv-bridge
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import json
from ultralytics import YOLO


class PersonDetector(Node):
    def __init__(self):
        super().__init__('person_detector')

        # YOLOv8 nano model — fastest, good enough for person detection
        # Downloads automatically on first run (~6MB)
        self.model = YOLO('yolov8n.pt')

        # Bridge to convert ROS2 Image messages to OpenCV frames
        self.bridge = CvBridge()

        # Subscribe to camera feed
        self.image_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10
        )

        # Publish selected target info to navigator
        self.target_pub = self.create_publisher(String, '/target_person', 10)

        # --- Tracking State ---
        self.selected_id = None   # Tracking ID of person user clicked
        self.detections = {}      # Current frame detections {id: bbox_dict}
        self.last_seen = {}       # Last known bbox per tracking ID

        self.get_logger().info('Person detector ready.')
        self.get_logger().info('Click on a person in the window to select them as target.')

    def image_callback(self, msg):
        """Called every time a new camera frame arrives."""

        # Convert ROS2 image message to OpenCV BGR frame
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Run YOLOv8 with tracking enabled
        # persist=True  → keeps the same ID for the same person across frames
        # classes=[0]   → only detect people (COCO class 0)
        results = self.model.track(
            frame,
            persist=True,
            classes=[0],
            verbose=False
        )

        self.detections = {}

        if results[0].boxes is not None:
            for box in results[0].boxes:

                # Skip detections without a tracking ID
                if box.id is None:
                    continue

                track_id = int(box.id.item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cx = (x1 + x2) // 2   # Bounding box center x
                cy = (y1 + y2) // 2   # Bounding box center y
                width = x2 - x1
                height = y2 - y1

                self.detections[track_id] = {
                    'x1': x1, 'y1': y1,
                    'x2': x2, 'y2': y2,
                    'cx': cx, 'cy': cy,
                    'width': width,
                    'height': height
                }

                # Always update last seen position
                self.last_seen[track_id] = self.detections[track_id].copy()

                # Green box normally, red box for selected target
                color = (0, 0, 255) if track_id == self.selected_id else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, f'ID:{track_id}',
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
                )

        # Publish target position and draw status bar
        self.publish_target(frame)

        # Show the window
        window_name = 'Person Detector - Click to select target'
        cv2.imshow(window_name, frame)
        cv2.setMouseCallback(window_name, self.mouse_click)
        cv2.waitKey(1)

    def mouse_click(self, event, x, y, flags, param):
        """Handle mouse clicks on the camera window."""
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        # Check if click lands inside any detected bounding box
        for track_id, det in self.detections.items():
            if det['x1'] < x < det['x2'] and det['y1'] < y < det['y2']:
                self.selected_id = track_id
                self.get_logger().info(f'Selected person ID: {track_id}')
                return

        # Click outside all boxes → deselect
        self.selected_id = None
        self.get_logger().info('Target deselected')

    def publish_target(self, frame):
        """
        Publish target person info to /target_person.

        Payload fields:
          id              → tracking ID of selected person
          status          → 'visible' or 'lost'
          normalized_x    → horizontal position in frame [-1.0 left .. 0.0 center .. 1.0 right]
          normalized_size → bounding box width / frame width (proxy for distance)
          cx, cy          → raw pixel center of bounding box
        """
        if self.selected_id is None:
            return

        img_width = frame.shape[1]

        if self.selected_id in self.detections:
            # Target is currently visible
            det = self.detections[self.selected_id]
            status = 'visible'
        elif self.selected_id in self.last_seen:
            # Target not visible — navigate to last known position
            det = self.last_seen[self.selected_id]
            status = 'lost'
            self.get_logger().info(
                f'Target {self.selected_id} lost — navigating to last seen position'
            )
        else:
            return

        # normalized_x: -1.0 = far left, 0.0 = center, 1.0 = far right
        normalized_x = (det['cx'] - img_width / 2) / (img_width / 2)

        # normalized_size: larger = closer to the person
        normalized_size = det['width'] / img_width

        payload = {
            'id': self.selected_id,
            'status': status,
            'normalized_x': round(normalized_x, 3),
            'normalized_size': round(normalized_size, 3),
            'cx': det['cx'],
            'cy': det['cy'],
        }

        # Draw status overlay on frame
        status_text = (
            f"Target {self.selected_id} | {status.upper()} "
            f"| x:{normalized_x:.2f} | size:{normalized_size:.2f}"
        )
        cv2.putText(
            frame, status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
        )

        msg = String()
        msg.data = json.dumps(payload)
        self.target_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PersonDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()