import time
import cv2
import numpy as np

from Tests.car.video_stream_fast import get_vid_fast


WIDTH = 1296
HEIGHT = 972
PORT = 5000
HOST = "0.0.0.0"


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
    cv2.namedWindow("Pi Camera Fast", cv2.WINDOW_AUTOSIZE)

    print("Starting fast stream...")
    stream = get_vid_fast(host=HOST, port=PORT, width=WIDTH, height=HEIGHT)

    last_print = time.time()
    frames = 0
    wait = waiting_frame("Waiting for frames...")

    try:
        while True:
            frame = stream.read()

            if frame is None:
                frame = wait
            else:
                frames += 1

            cv2.imshow("Pi Camera Fast", frame)

            now = time.time()
            if now - last_print >= 1:
                print(f"Fast frames displayed: {frames}")
                frames = 0
                last_print = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        stream.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
