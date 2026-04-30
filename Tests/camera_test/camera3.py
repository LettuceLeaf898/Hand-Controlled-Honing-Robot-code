import cv2

# Define the UDP receiver pipeline string
# Replace '5000' with your specific port and 'H264' with your codec if different
pipeline = (
    "udpsrc port=5000 ! "
    "application/x-rtp, media=video, encoding-name=H264 ! "
    "rtph264depay ! h264parse ! avdec_h264 ! "
    "videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('UDP Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
