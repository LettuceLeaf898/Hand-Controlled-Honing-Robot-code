import argparse
import socket
import sys
import time
import tkinter as tk


KEY_TO_COMMAND = {
    "s": "F",
    "a": "R",
    "w": "B",
    "d": "L",
}


class KeyboardDriveClient:
    def __init__(self, host: str, port: int, send_interval: float) -> None:
        self.host = host
        self.port = port
        self.send_interval = send_interval
        self.sock: socket.socket | None = None

        self.pressed_keys: set[str] = set()
        self.key_order: list[str] = []
        self.current_command = "S"

        self.root = tk.Tk()
        self.root.title("WASD Drive Controller")
        self.root.geometry("460x220")
        self.root.resizable(False, False)
        self.root.configure(bg="#10131a")

        self.status_var = tk.StringVar(value="Disconnected")
        self.command_var = tk.StringVar(value="Current command: S")

        self._build_ui()
        self._bind_keys()

    def _build_ui(self) -> None:
        title = tk.Label(
            self.root,
            text="WASD Drive Controller",
            font=("Segoe UI", 18, "bold"),
            fg="#e8f0ff",
            bg="#10131a",
        )
        title.pack(pady=(16, 6))

        info = tk.Label(
            self.root,
            text="Hold W/A/S/D to drive. Release key to stop.\nPress Q or close window to exit.",
            font=("Segoe UI", 11),
            fg="#c0ccdf",
            bg="#10131a",
        )
        info.pack(pady=(0, 10))

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Consolas", 10),
            fg="#73d2de",
            bg="#10131a",
        )
        status.pack()

        command = tk.Label(
            self.root,
            textvariable=self.command_var,
            font=("Consolas", 14, "bold"),
            fg="#f6f7fb",
            bg="#10131a",
        )
        command.pack(pady=(8, 0))

    def _bind_keys(self) -> None:
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.focus_force()

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2.0)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(None)
        self.status_var.set(f"Connected to {self.host}:{self.port}")

    def send_command(self, cmd: str) -> None:
        if self.sock is None:
            return
        try:
            self.sock.sendall(f"{cmd}\n".encode("utf-8"))
        except OSError:
            self.status_var.set("Connection lost")
            self.shutdown()

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "q":
            self.shutdown()
            return

        if key in KEY_TO_COMMAND and key not in self.pressed_keys:
            self.pressed_keys.add(key)
            self.key_order.append(key)
            self.current_command = KEY_TO_COMMAND[self.key_order[-1]]
            self.command_var.set(f"Current command: {self.current_command}")

    def on_key_release(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key not in KEY_TO_COMMAND:
            return

        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
        if key in self.key_order:
            self.key_order = [k for k in self.key_order if k != key]

        if self.key_order:
            self.current_command = KEY_TO_COMMAND[self.key_order[-1]]
        else:
            self.current_command = "S"

        self.command_var.set(f"Current command: {self.current_command}")

    def heartbeat(self) -> None:
        # Re-send command periodically so the car keeps moving while key is held.
        self.send_command(self.current_command)
        self.root.after(int(self.send_interval * 1000), self.heartbeat)

    def run(self) -> int:
        try:
            self.connect()
        except OSError as error:
            print(f"Failed to connect to {self.host}:{self.port}: {error}", file=sys.stderr)
            return 1

        self.send_command("S")
        self.heartbeat()
        self.root.mainloop()
        return 0

    def shutdown(self) -> None:
        try:
            self.send_command("S")
            time.sleep(0.05)
        finally:
            if self.sock is not None:
                try:
                    self.sock.close()
                finally:
                    self.sock = None
            if self.root.winfo_exists():
                self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keyboard teleop client for car server (WASD)")
    parser.add_argument("--host", default="192.168.40.48", help="Car server host")
    parser.add_argument("--port", type=int, default=5001, help="Car server port")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Seconds between repeated command sends while key is held",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = KeyboardDriveClient(host=args.host, port=args.port, send_interval=args.interval)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
