import cv2

# Load pre-trained HOG descriptor
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

video_capture = cv2.VideoCapture(0)
tracker = None

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    # 1. Detection Phase (Only if we aren't already tracking)
    if tracker is None:
        (rects, weights) = hog.detectMultiScale(frame, winStride=(4, 4), padding=(8, 8), scale=1.05)
        
        for (x, y, w, h) in rects:
            # Initialize tracker on the FIRST person found
            tracker = cv2.legacy.TrackerCSRT_create()
            tracker.init(frame, (x, y, w, h))
            break # Stop after finding one person to track

    # 2. Tracking Phase
    else:
        success, box = tracker.update(frame)
        if success:
            (x, y, w, h) = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "Tracking", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        else:
            # If tracking fails, reset so detection can try again
            tracker = None

    cv2.imshow('People Detection & Tracking', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()