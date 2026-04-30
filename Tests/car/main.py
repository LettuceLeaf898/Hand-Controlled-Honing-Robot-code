import cv2
from Tests.car.video_stream import get_vid

stream = get_vid("100.70.33.84", 5000, 1296, 972)

while True:
    frame = stream.read()
    if frame is None:
        continue

    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

stream.stop()
cv2.destroyAllWindows()

