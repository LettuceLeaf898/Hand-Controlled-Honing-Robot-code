import cv2

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    paused = False
    last_frame = None
    current_key = "None"

    print("Controls: W,A,S,D | P: Pause/Resume | Q: Quit")

    while True:
        # Only read a new frame if NOT paused
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            # Store this as our "frozen" frame
            last_frame = frame.copy()
        else:
            # If paused, we just keep using the last successful frame
            frame = last_frame.copy()

        # Check keys
        key = cv2.waitKey(1) & 0xFF

        if key == ord('p'):
            paused = not paused  # Toggle the pause state
            current_key = "P - Toggle Pause"
        elif key == ord('w'):
            current_key = "W - Forward"
        elif key == ord('a'):
            current_key = "A - Left"
        elif key == ord('s'):
            current_key = "S - Backward"
        elif key == ord('d'):
            current_key = "D - Right"
        elif key == ord('q'):
            break

        # Visual indicator for Pause
        status_text = "STATUS: PAUSED" if paused else "STATUS: LIVE"
        color = (0, 0, 255) if paused else (0, 255, 0) # Red if paused, Green if live

        cv2.putText(frame, status_text, (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Last Input: {current_key}", (50, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow('WASD + Pause Detection', frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()