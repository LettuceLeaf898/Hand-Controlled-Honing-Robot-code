#!/usr/bin/env python3
"""
navigator.py
------------
ROS2 node that:
  - Subscribes to /target_person (from person_detector.py)
  - Drives the robot toward the selected person
  - Uses normalized_x to steer left/right
  - Uses normalized_size as a proxy for distance (stops when close enough)
  - If target is 'lost', drives to last known position using odometry
  - Publishes velocity commands to /cmd_vel

Subscribed Topics:
  /target_person  (std_msgs/String)   JSON payload from person_detector
  /odom           (nav_msgs/Odometry) Robot position from wheel encoders

Published Topics:
  /cmd_vel  (geometry_msgs/Twist)  Velocity commands to drive the robot

Requirements:
  sudo apt install ros-jazzy-nav-msgs
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import json
import math


# --- Tuning Parameters ---
# Adjust these to change robot behaviour

LINEAR_SPEED = 0.3        # Max forward speed (m/s)
ANGULAR_SPEED = 0.6       # Max turning speed (rad/s)
STOP_SIZE = 0.35          # Stop when person's box fills this fraction of frame
                          # (higher = stop closer to person)
DEAD_ZONE = 0.1           # Ignore small left/right errors (prevents jitter)
LOST_DRIVE_SPEED = 0.2    # Speed when driving to last seen position
ARRIVED_DISTANCE = 0.3    # How close to last seen position counts as arrived (m)


class Navigator(Node):
    def __init__(self):
        super().__init__('navigator')

        # Subscribe to target person info from person_detector
        self.target_sub = self.create_subscription(
            String,
            '/target_person',
            self.target_callback,
            10
        )

        # Subscribe to odometry for position tracking
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        # Publish velocity commands
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # --- State ---
        self.current_target = None       # Latest target payload dict
        self.robot_x = 0.0              # Current robot x position
        self.robot_y = 0.0              # Current robot y position
        self.robot_yaw = 0.0            # Current robot heading
        self.last_seen_x = None         # Last seen target robot x
        self.last_seen_y = None         # Last seen target robot y
        self.target_lost = False        # Whether target is currently lost

        # Control loop runs at 20Hz
        self.timer = self.create_timer(0.05, self.control_loop)

        self.get_logger().info('Navigator ready. Waiting for target...')

    def odom_callback(self, msg):
        """Update robot position from odometry."""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

        # Convert quaternion to yaw angle
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.robot_yaw = math.atan2(siny_cosp, cosy_cosp)

    def target_callback(self, msg):
        """Receive target info from person_detector."""
        try:
            self.current_target = json.loads(msg.data)

            if self.current_target['status'] == 'visible':
                # Save robot position when we last saw the target
                self.last_seen_x = self.robot_x
                self.last_seen_y = self.robot_y
                self.target_lost = False

            elif self.current_target['status'] == 'lost':
                self.target_lost = True

        except json.JSONDecodeError:
            self.get_logger().warn('Failed to parse target message')

    def control_loop(self):
        """Main control loop — runs at 20Hz."""
        cmd = Twist()  # Default: stop

        if self.current_target is None:
            # No target selected yet — stay still
            self.cmd_pub.publish(cmd)
            return

        if not self.target_lost:
            # --- Target is VISIBLE --- drive toward them ---
            cmd = self.drive_toward_visible_target()
        else:
            # --- Target is LOST --- drive to last seen position ---
            cmd = self.drive_to_last_seen()

        self.cmd_pub.publish(cmd)

    def drive_toward_visible_target(self):
        """
        Drive toward visible target using camera info.

        normalized_x: -1.0 = far left, 0.0 = center, 1.0 = far right
        normalized_size: larger = closer to person
        """
        cmd = Twist()
        target = self.current_target

        normalized_x = target.get('normalized_x', 0.0)
        normalized_size = target.get('normalized_size', 0.0)

        # Stop if close enough to person
        if normalized_size >= STOP_SIZE:
            self.get_logger().info('Reached target person — stopping')
            return cmd  # zero velocity = stop

        # Forward speed — slow down as we get closer
        closeness = normalized_size / STOP_SIZE  # 0.0 = far, 1.0 = at stop distance
        cmd.linear.x = LINEAR_SPEED * (1.0 - closeness * 0.5)

        # Turning — steer toward center of bounding box
        if abs(normalized_x) > DEAD_ZONE:
            cmd.angular.z = -ANGULAR_SPEED * normalized_x
            # Negative because: positive normalized_x = person is to the right
            # = we need to turn right = negative angular.z in ROS

        return cmd

    def drive_to_last_seen(self):
        """
        Drive to last known position of target using odometry.
        Once arrived, stop and wait.
        """
        cmd = Twist()

        if self.last_seen_x is None or self.last_seen_y is None:
            return cmd  # No last seen position recorded yet

        # Calculate distance to last seen position
        dx = self.last_seen_x - self.robot_x
        dy = self.last_seen_y - self.robot_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < ARRIVED_DISTANCE:
            # Arrived at last seen position — stop and wait
            self.get_logger().info('Arrived at last seen position — waiting for target')
            self.current_target = None  # Reset so we stop publishing commands
            return cmd

        # Calculate angle to last seen position
        target_angle = math.atan2(dy, dx)
        angle_error = target_angle - self.robot_yaw

        # Normalize angle to [-pi, pi]
        while angle_error > math.pi:
            angle_error -= 2 * math.pi
        while angle_error < -math.pi:
            angle_error += 2 * math.pi

        # Turn toward target angle first, then drive forward
        if abs(angle_error) > 0.3:
            # Turn to face target
            cmd.angular.z = ANGULAR_SPEED * (angle_error / abs(angle_error))
        else:
            # Drive forward toward target
            cmd.linear.x = LOST_DRIVE_SPEED
            cmd.angular.z = 0.5 * angle_error  # Small correction while driving

        return cmd


def main(args=None):
    rclpy.init(args=args)
    node = Navigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Make sure robot stops when node shuts down
        stop_cmd = Twist()
        node.cmd_pub.publish(stop_cmd)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()