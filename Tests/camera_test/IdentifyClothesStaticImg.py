import cv2
import numpy as np
from ultralytics import YOLO
import webcolors

def get_color_name(rgb_triplet):
    try:
        # Convert RGB to Name directly if it's an exact match
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
    return tuple(np.median(pixels, axis=0).astype(int))
model = YOLO("yolov8n.pt")

img = cv2.imread("people.jpg")

if img is None:
    raise ValueError("Image not found")

cv2.namedWindow("Color Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Color Detection", 800, 600)

results = model(img)[0]

for box in results.boxes:

    if int(box.cls.item()) != 0:
        continue

    x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())

    shirt = img[y1:y1+(y2-y1)//3, x1:x2]
    pants = img[y1+(y2-y1)//2:y2, x1:x2]

    s_color = get_dominant_color(shirt)
    p_color = get_dominant_color(pants)

    s_name = get_color_name(s_color[::-1])
    p_name = get_color_name(p_color[::-1])

    print("-" * 30)
    print(f"Detected Person at [{x1}, {y1}]")
    print(f"Shirt Color: {s_name} (RGB: {s_color[::-1]})")
    print(f"Pants Color: {p_name} (RGB: {p_color[::-1]})")
    
    cv2.rectangle(img,(x1,y1),(x2,y2),(0,255,0),2)

    cv2.putText(img,f"Shirt: {s_name}",(x1,y1-25),
                cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2)

    cv2.putText(img,f"Pants: {p_name}",(x1,y1-5),
                cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2)

cv2.imshow("Color Detection",img)
cv2.waitKey(0)
cv2.destroyAllWindows()