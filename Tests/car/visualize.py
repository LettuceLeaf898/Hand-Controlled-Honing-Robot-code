import time
import cv2
import numpy as np

from Tests.car.video_stream import get_vid


WIDTH = 320
HEIGHT = 240
PORT = 5000


def waiting_frame(message: str):
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    cv2.putText(
        img,
        message,
        (10, HEIGHT // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return img


def main():
    # IMPORTANT: close VLC first. VLC and Python cannot both listen on UDP 5000.
    cv2.namedWindow("Pi Camera", cv2.WINDOW_NORMAL)

    print("Starting stream...")
    stream = get_vid(host="0.0.0.0", port=PORT, width=WIDTH, height=HEIGHT)

    last_print = time.time()
    frames = 0

    try:
        while True:
            frame = stream.read()

            if frame is None:
                frame = waiting_frame("Waiting for frames...")
            else:
                frames += 1

            cv2.imshow("Pi Camera", frame)

            now = time.time()
            if now - last_print >= 1:
                print(f"Frames received: {frames}")
                frames = 0
                last_print = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        stream.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()