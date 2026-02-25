import numpy as np
import matplotlib.pyplot as plt
import cv2

from PIL import Image
from Util import get_limited

yellow = [0, 255, 255]
#test code for camera
cap = cv2.VideoCapture(0) 
t = True
while (t):
    ret, frame = cap.read()
    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    lowerLimit, upperLimit = get_limited(color= yellow)
    mask = cv2.inRange(hsvImage, lowerLimit, upperLimit)
    
    mask_ = Image.fromarray(mask)
    
    bbox = mask_.getbbox()
    
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 5)
    
    
    cv2.imshow('frame', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        t = False
        break
        
    
cap.release()

cv2.destroyAllWindows()