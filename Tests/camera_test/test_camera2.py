import cv2
import os
from flask import Flask, Response

# 1. FORCE OpenCV to use the correct protocols (Must be at the very top)
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'protocol_whitelist;file,rtp,udp|buffer_size;1024000'

app = Flask(__name__)

def generate_frames():
    # 2. Use '@' and force the FFMPEG backend
    # If '@0.0.0.0' fails, try 'udp://@100.70.33.85:5000'
    cap = cv2.VideoCapture("udp://@0.0.0.0:5000", cv2.CAP_FFMPEG)
    
    # 3. Check if the stream actually opened
    if not cap.isOpened():
        print("Error: Could not open UDP stream. Check if Pi is sending data.")
        return

    while True:
        success, frame = cap.read()
        if not success:
            # If a frame is dropped, don't crash, just keep trying
            continue
        
        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '<h1>Pi Stream</h1><img src="/video_feed" width="100%">'

if __name__ == "__main__":
    # Disable debug mode to prevent dual-initialization of the camera
    app.run(host='0.0.0.0', port=8080, debug=False)
