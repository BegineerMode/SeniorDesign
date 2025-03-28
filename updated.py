import cv2
import torch
from ultralytics import YOLO
import threading
import numpy as np
from queue import Queue
import time
import serial
from scipy.spatial import distance as dist  # For accurate person matching
import math

# -------------------------------
# Serial Communication with Arduino
# -------------------------------
arduino_port = "COM6"
baud_rate = 9600

try:
    arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
    print(f"Connected to Arduino on {arduino_port}")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    arduino = None

# RTSP stream URLs for both cameras
stream_url_1 = "http://192.168.1.134:8080"
stream_url_2 = "http://192.168.1.107:8080"

# Load YOLO model
model = YOLO('D:/runs/detect/train11/weights/last.pt')

# Camera parameters
focal_length = 700  # Focal length in pixels
baseline = 0.3048   # Distance between cameras in meters

# Frame size and queue setup
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
QUEUE_SIZE = 10

# Frame queues
queue1 = Queue(maxsize=QUEUE_SIZE)
queue2 = Queue(maxsize=QUEUE_SIZE)

# -------------------------------
# Virtual Zone Class with Independent Corner Dragging
# -------------------------------
class VirtualZone:
    def __init__(self, x, y, w, h):
        self.corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        self.dragging_corner = None
        self.corner_size = 10

    def draw(self, frame):
        """Draw the virtual zone with draggable corners."""
        for i in range(4):
            cv2.line(frame, self.corners[i], self.corners[(i + 1) % 4], (0, 255, 0), 2)
            cv2.circle(frame, self.corners[i], self.corner_size, (0, 0, 255), -1)

    def handle_mouse_event(self, event, x, y):
        """Handle mouse events for dragging corners."""
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, (cx, cy) in enumerate(self.corners):
                if abs(x - cx) < self.corner_size and abs(y - cy) < self.corner_size:
                    self.dragging_corner = i
                    break
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging_corner is not None:
            self.corners[self.dragging_corner] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging_corner = None

    def is_inside(self, x, y):
        """Check if a point (x, y) is inside the virtual zone."""
        contour = np.array(self.corners, dtype=np.int32)
        return cv2.pointPolygonTest(contour, (x, y), False) >= 0


# Initialize virtual zone
zone = VirtualZone(100, 100, 200, 150)

# -------------------------------
# Mouse Event Callback
# -------------------------------
def mouse_callback(event, x, y, flags, param):
    zone.handle_mouse_event(event, x, y)

cv2.namedWindow("Combined Feed")
cv2.setMouseCallback("Combined Feed", mouse_callback)

# -------------------------------
# Frame Capture Thread
# -------------------------------
def capture_frames(cap, queue, cam_id):
    """Thread function to capture frames from camera."""
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Cannot read from camera {cam_id}")
            break

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        if queue.full():
            queue.get()
        queue.put(frame)

# -------------------------------
# Distance Calculation Using Bounding Box Centers
# -------------------------------
def calculate_distance(box1, box2):
    """Calculate distance using the polynomial interpolation directly from disparity."""
    x1 = (box1[0] + box1[2]) / 2
    x2 = (box2[0] + box2[2]) / 2

    # Calculate disparity
    disparity = abs(x1 - x2)

    if disparity < 1:
        return None

    # Use the polynomial interpolation equation
    distance_feet = (
        -0.0013 * (disparity ** 3)
        + 0.4543 * (disparity ** 2)
        - 53.9225 * disparity
        + 2256.4096
    )

    # Ensure the distance is non-negative and valid
    if distance_feet < 0 or math.isinf(distance_feet) or math.isnan(distance_feet):
        return None

    return distance_feet




# -------------------------------
# Nearest Neighbor Matching for Accurate Pairing
# -------------------------------
def match_persons(results1, results2, confidence_threshold=0.5):
    """Match persons across both frames using nearest neighbors."""
    persons1 = [box.xyxy[0].tolist() for box in results1.boxes if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold]
    persons2 = [box.xyxy[0].tolist() for box in results2.boxes if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold]

    if not persons1 or not persons2:
        return []

    # Match persons based on x-coordinates (disparity calculation)
    pairs = []
    for p1 in persons1:
        distances = [abs((p1[0] + p1[2]) / 2 - (p2[0] + p2[2]) / 2) for p2 in persons2]
        min_idx = np.argmin(distances)
        pairs.append((p1, persons2[min_idx]))

    return pairs


# -------------------------------
# Camera Initialization
# -------------------------------
cap1 = cv2.VideoCapture(stream_url_1)
cap2 = cv2.VideoCapture(stream_url_2)

if not cap1.isOpened() or not cap2.isOpened():
    print("Error: Could not open streams.")
    exit()

# Start frame capture threads
thread1 = threading.Thread(target=capture_frames, args=(cap1, queue1, 1))
thread2 = threading.Thread(target=capture_frames, args=(cap2, queue2, 2))
thread1.start()
thread2.start()

# -------------------------------
# Display Loop
# -------------------------------
while True:
    if not queue1.empty() and not queue2.empty():
        frame1 = queue1.get()
        frame2 = queue2.get()

        # YOLO Inference in Separate Threads
        results1 = model.predict(frame1, verbose=False)[0]
        results2 = model.predict(frame2, verbose=False)[0]

        frame1_resized = results1.plot()
        frame2_resized = results2.plot()

        zone.draw(frame1_resized)
        zone.draw(frame2_resized)

        # Only match persons with confidence >= 0.5
        pairs = match_persons(results1, results2, confidence_threshold=0.5)

        intrusion_detected = False
        distances = []
        disparities = []

        for box1, box2 in pairs:
            distance = calculate_distance(box1, box2)
            disparity = abs((box1[0] + box1[2]) / 2 - (box2[0] + box2[2]) / 2)

            if distance:
                distances.append(distance)
                disparities.append(disparity)

                # Draw distances
                center_x1 = int((box1[0] + box1[2]) / 2)
                center_y1 = int((box1[1] + box1[3]) / 2)

                color = (0, 0, 255) if distance <= 5 else (0, 255, 0)
                cv2.putText(frame1_resized, f"{distance:.2f} ft", (center_x1, center_y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                if distance <= 5 and zone.is_inside(center_x1, center_y1):
                    intrusion_detected = True

        if intrusion_detected and arduino:
            arduino.write(b'ALARM\n')

        # Combine frames into a single display window
        combined_height = FRAME_HEIGHT + 300  # Combined height for both camera feeds and distance window
        combined_frame = np.zeros((combined_height, FRAME_WIDTH * 2, 3), dtype=np.uint8)

        # Place Camera 1 Feed on the left
        combined_frame[:FRAME_HEIGHT, :FRAME_WIDTH] = frame1_resized

        # Place Camera 2 Feed on the right
        combined_frame[:FRAME_HEIGHT, FRAME_WIDTH:] = frame2_resized

        # Add distance information below
        distance_window = np.zeros((300, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        for i, dist in enumerate(distances):
            cv2.putText(distance_window, f"Person {i+1}: {dist:.2f} ft", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Place Distance info below the camera feeds
        combined_frame[FRAME_HEIGHT:] = distance_window

        # Display disparity in a separate window
        disparity_window = np.zeros((300, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        for i, disp in enumerate(disparities):
            cv2.putText(disparity_window, f"Disparity {i+1}: {disp:.2f} px", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Show combined window with distance and disparity
        cv2.imshow("Combined Feed", combined_frame)
        cv2.imshow("Disparity Feed", disparity_window)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap1.release()
cap2.release()
cv2.destroyAllWindows()


































