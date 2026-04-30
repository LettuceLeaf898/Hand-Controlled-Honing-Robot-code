import subprocess
import threading
from typing import Optional

import cv2
import numpy as np


class FastUDPStream:
    def __init__(
        self,
        host: str,
        port: int,
        width: int,
        height: int,
        ffmpeg_path: str = "ffmpeg",
    ):
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self.frame_size = width * height * 3
        self.ffmpeg_path = ffmpeg_path

        self.proc: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        self.running = False

        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

    def start(self) -> "FastUDPStream":
        # Keep UDP queue very small for low-latency "latest frame" behavior.
        url = f"udp://{self.host}:{self.port}?overrun_nonfatal=1&fifo_size=65536"

        # Preserve aspect ratio and avoid visual crop/cutoff while keeping output size fixed.
        vf_filter = (
            f"scale={self.width}:{self.height}:"
            "force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black"
        )

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-thread_queue_size",
            "1",
            "-fflags",
            "nobuffer+discardcorrupt",
            "-flags",
            "low_delay",
            "-probesize",
            "1000000",
            "-analyzeduration",
            "1000000",
            "-f",
            "mpegts",
            "-i",
            url,
            "-an",
            "-vf",
            vf_filter,
            "-pix_fmt",
            "bgr24",
            "-f",
            "rawvideo",
            "pipe:1",
        ]

        print("FFmpeg command (fast):")
        print(" ".join(cmd))

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        self.running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()

        self.stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
        self.stderr_thread.start()

        return self

    def _stderr_loop(self) -> None:
        if self.proc is None or self.proc.stderr is None:
            return

        for line in iter(self.proc.stderr.readline, b""):
            msg = line.decode(errors="replace").strip()
            if msg:
                print(f"[ffmpeg-fast] {msg}")

    def _read_exactly(self, size: int) -> Optional[bytes]:
        if self.proc is None or self.proc.stdout is None:
            return None

        data = bytearray(size)
        mv = memoryview(data)
        got = 0

        while got < size and self.running:
            n = self.proc.stdout.readinto(mv[got:])
            if n is None:
                chunk = self.proc.stdout.read(size - got)
                if not chunk:
                    return None
                mv[got : got + len(chunk)] = chunk
                got += len(chunk)
                continue
            if n == 0:
                return None
            got += n

        return bytes(data)

    def _reader_loop(self) -> None:
        while self.running:
            raw = self._read_exactly(self.frame_size)
            if raw is None:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                (self.height, self.width, 3)
            )

            with self._lock:
                self._latest_frame = frame

        self.running = False
        print("Fast reader loop stopped.")

    def read(self) -> Optional[np.ndarray]:
        # No frame copy here for higher throughput.
        with self._lock:
            return self._latest_frame

    def read_copy(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def stop(self) -> None:
        self.running = False

        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

        self.proc = None


def get_vid_fast(
    host: str = "0.0.0.0",
    port: int = 5000,
    width: int = 320,
    height: int = 240,
    ffmpeg_path: str = "ffmpeg",
) -> FastUDPStream:
    return FastUDPStream(host, port, width, height, ffmpeg_path).start()


if __name__ == "__main__":
    stream = get_vid_fast(host="0.0.0.0", port=5000, width=320, height=240)

    try:
        while True:
            frame = stream.read()
            if frame is None:
                continue

            cv2.imshow("Pi Camera OpenCV Fast", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        stream.stop()
        cv2.destroyAllWindows()
