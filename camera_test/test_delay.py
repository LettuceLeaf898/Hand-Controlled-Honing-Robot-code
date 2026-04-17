import subprocess
import threading
import queue
import cv2
import numpy as np
import sys

WIDTH = 320
HEIGHT = 240
PORT = 5000

latest = queue.Queue(maxsize=1)

def start_ffmpeg():
    cmd = [
        "ffmpeg",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-i", f"udp://0.0.0.0:{PORT}",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-"
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**8,
    )

def reader(proc):
    frame_size = WIDTH * HEIGHT * 3
    if proc.stdout is None:
        raise RuntimeError("ffmpeg stdout unavailable")

    while True:
        raw = proc.stdout.read(frame_size)
        if len(raw) != frame_size:
            continue

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))

        if latest.full():
            try:
                latest.get_nowait()
            except queue.Empty:
                pass

        latest.put(frame)

def main():
    proc = start_ffmpeg()
    threading.Thread(target=reader, args=(proc,), daemon=True).start()

    while True:
        try:
            frame = latest.get(timeout=1.0)
        except queue.Empty:
            continue

        cv2.imshow("Latest Frame Only", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    proc.terminate()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)