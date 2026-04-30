#!/usr/bin/env python3

import argparse
import json
import socket
import sys
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class AutoFollowClient(Node):
    def __init__(
        self,
        host: str,
        port: int,
        send_interval: float,
        target_size: float,
        size_deadband: float,
        turn_deadband: float,
        lost_timeout: float,
    ):
        super().__init__("auto_follow_client")

        self.host = host
        self.port = port
        self.send_interval = send_interval

        # Tuning values
        self.target_size = target_size          # desired person bbox width / image width
        self.size_deadband = size_deadband      # distance tolerance
        self.turn_deadband = turn_deadband      # center tolerance
        self.lost_timeout = lost_timeout

        self.sock: Optional[socket.socket] = None

        self.last_target = None
        self.last_target_time = 0.0
        self.current_command = "S"
        self.last_sent_command = None

        self.target_sub = self.create_subscription(
            String,
            "/target_person",
            self.target_callback,
            10,
        )

        self.timer = self.create_timer(self.send_interval, self.control_loop)

        self.connect()
        self.get_logger().info(f"Connected to car server at {self.host}:{self.port}")
        self.get_logger().info("Auto-follow client ready.")

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2.0)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(None)

    def target_callback(self, msg: String) -> None:
        try:
            self.last_target = json.loads(msg.data)
            self.last_target_time = time.time()
        except json.JSONDecodeError:
            self.get_logger().warn(f"Bad target JSON: {msg.data}")

    def decide_command(self) -> str:
        now = time.time()

        if self.last_target is None:
            return "S"

        if now - self.last_target_time > self.lost_timeout:
            return "S"

        status = self.last_target.get("status", "lost")
        if status != "visible":
            return "S"

        x = float(self.last_target.get("normalized_x", 0.0))
        size = float(self.last_target.get("normalized_size", 0.0))

        # x < 0 means person is left of center.
        # x > 0 means person is right of center.
        if x < -self.turn_deadband:
            return "R"

        if x > self.turn_deadband:
            return "L"

        # Person is centered enough. Now control distance.
        if size < self.target_size - self.size_deadband:
            return "F"

        if size > self.target_size + self.size_deadband:
            return "B"

        return "S"

    def send_command(self, cmd: str) -> None:
        if self.sock is None:
            return

        try:
            self.sock.sendall(f"{cmd}\n".encode("utf-8"))
            self.last_sent_command = cmd
        except OSError as error:
            self.get_logger().error(f"Connection lost: {error}")
            self.safe_stop()
            rclpy.shutdown()

    def control_loop(self) -> None:
        cmd = self.decide_command()
        self.current_command = cmd
        self.send_command(cmd)

        self.get_logger().info(
            f"cmd={cmd} target={self.last_target}",
            throttle_duration_sec=0.5,
        )

    def safe_stop(self) -> None:
        try:
            if self.sock is not None:
                self.sock.sendall(b"S\n")
                time.sleep(0.05)
        except OSError:
            pass

        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def destroy_node(self):
        self.safe_stop()
        super().destroy_node()


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-follow client using /target_person")
    parser.add_argument("--host", default="192.168.40.48", help="Car server host")
    parser.add_argument("--port", type=int, default=5001, help="Car server port")
    parser.add_argument("--interval", type=float, default=0.1, help="Command send interval")

    # Tune these live.
    parser.add_argument("--target-size", type=float, default=0.80)
    parser.add_argument("--size-deadband", type=float, default=0.12)
    parser.add_argument("--turn-deadband", type=float, default=0.30)
    parser.add_argument("--lost-timeout", type=float, default=0.5)

    return parser.parse_args()


def main(args=None):
    cli_args = parse_args()

    rclpy.init(args=args)

    node = AutoFollowClient(
        host=cli_args.host,
        port=cli_args.port,
        send_interval=cli_args.interval,
        target_size=cli_args.target_size,
        size_deadband=cli_args.size_deadband,
        turn_deadband=cli_args.turn_deadband,
        lost_timeout=cli_args.lost_timeout,
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
