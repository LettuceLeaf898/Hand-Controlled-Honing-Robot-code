from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

# Initialize the camera
picam2 = Picamera2()
# Standard resolution for smooth streaming
config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # Capture a frame as an array
        frame = picam2.capture_array()
        
        # Convert the frame to JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Yield the output in a format the browser understands (MJPEG)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # '0.0.0.0' allows the server to be accessed by other devices on the network
    app.run(host='0.0.0.0', port=5000)