import cv2
import os
import sys

# Replace with your Pi's IP address
stream_url = 'tcp://10.25.68.100:5000'

os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "fflags;nobuffer|flags;low_delay|avioflags;direct|probesize;32|analyzeduration;0",
)


def open_low_latency_capture(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def read_latest_frame(cap: cv2.VideoCapture):
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


cap = open_low_latency_capture(stream_url)
if not cap.isOpened():
    print(f"Error: could not open stream {stream_url}", file=sys.stderr)
    raise SystemExit(1)

while True:
    ret, frame = read_latest_frame(cap)
    if not ret:
        break
    
    cv2.imshow('Remote Pi Feed', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()