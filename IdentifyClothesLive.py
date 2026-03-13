import cv2
import numpy as np
from ultralytics import YOLO
import webcolors

def get_color_name(rgb_triplet):
    try:
        
        return webcolors.rgb_to_name(rgb_triplet)
    except ValueError:
        # If no exact match, we manually find the 'closest' color
        min_dist = float("inf")
        closest_name = "unknown"

        # Use webcolors.name_to_rgb to get the standard list
        # We iterate through the CSS3 color names
        for name in webcolors.names("css3"):
            # Get the RGB for this standard color name
            standard_rgb = webcolors.name_to_rgb(name)

            # Euclidean distance between your color and the standard color
            dist = ( (standard_rgb.red - rgb_triplet[0])**2 + 
                     (standard_rgb.green - rgb_triplet[1])**2 + 
                     (standard_rgb.blue - rgb_triplet[2])**2 )

            if dist < min_dist:
                min_dist = dist
                closest_name = name

        return closest_name
    
def get_dominant_color(image_roi):
    if image_roi.size == 0:
        return (0, 0, 0)
    
    # Shrink the ROI by 20% on each side to avoid background/borders
    h, w, _ = image_roi.shape
    margin_h, margin_w = int(h * 0.2), int(w * 0.2)
    center_roi = image_roi[margin_h:h-margin_h, margin_w:w-margin_w]
    
    if center_roi.size == 0: return (0,0,0)

    # Use median instead of mean to ignore outlier pixels (like buttons or shadows)
    pixels = center_roi.reshape(-1, 3)
    return tuple(np.mean(pixels, axis=0).astype(int))

def apply_clahe(frame):
    # Convert to LAB color space to adjust lightness without affecting colors
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to the L-channel (Lightness)
    clahe = cv2.createCLAHE(clipLimit=3.0, tqileGridSize=(8,8))
    cl = clahe.apply(l)
    
    # Merge back and convert to BGR
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)



def identify_clothing(frame, model):
    """
    Processes a single frame, detects people, and labels their clothes.
    Returns the processed frame.
    """
    frame = cv2.convertScaleAbs(frame, alpha = 1.5, beta = 10)  # Ensure frame is in the right format for YOLO
    results = model(frame, verbose=False)[0]
    
    for box in results.boxes:
        if int(box.cls.item()) != 0:  # Skip if not a person
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

        # Ensure coordinates are within frame boundaries
        h, w, _ = frame.shape
        y1, y2 = max(0, y1), min(h, y2)
        x1, x2 = max(0, x1), min(w, x2)

        person_height = y2 - y1
        
        head_gap = int(person_height *0.2)
        
        shirt_roi_noHead = frame[y1 + head_gap : y1 + head_gap + person_height//3, x1 : x2]
        pants_roi_noHead = frame[y1 + head_gap + person_height//2 : y2, x1 : x2]
        
        # 1. Define ROI for Shirt and Pants
        shirt_roi = frame[y1 : y1 + (y2 - y1) // 3, x1 : x2]
        pants_roi = frame[y1 + (y2 - y1) // 2 : y2, x1 : x2]

        # 2. Get Colors
        s_color = get_dominant_color(shirt_roi)
        p_color = get_dominant_color(pants_roi)
        
        s_colorNH = get_dominant_color(shirt_roi_noHead)
        p_colorNH = get_dominant_color(pants_roi_noHead)

        s_name = get_color_name(s_color[::-1])
        p_name = get_color_name(p_color[::-1])
        
        s_nameNH = get_color_name(s_colorNH[::-1])
        p_nameNH = get_color_name(p_colorNH[::-1])

        # 3. Draw on the frame
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"S: {s_nameNH}", (x1, y1 - 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(frame, f"P: {p_nameNH}", (x1, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
    return frame


model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Call your function
    processed_frame = identify_clothing(frame, model)

    cv2.imshow("Live AI Detection", processed_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()