import cv2

# GStreamer pipeline string for receiving UDP H.264
pipeline = (
    "udpsrc port=5000 ! "
    "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! "
    "rtph264depay ! h264parse ! avdec_h264 ! "
    "videoconvert ! appsink"
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Error: Could not open stream.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Raspberry Pi Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

