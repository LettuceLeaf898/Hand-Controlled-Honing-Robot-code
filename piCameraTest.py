import cv2

# Replace with your Pi's IP address
stream_url = 'tcp://10.25.68.100:5000'
cap = cv2.VideoCapture(stream_url)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    cv2.imshow('Remote Pi Feed', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()