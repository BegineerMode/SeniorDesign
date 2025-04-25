import cv2
import torch
from ultralytics import YOLO
import threading
import numpy as np
from queue import Queue
import time
import serial
import math
import smtplib
from email.mime.text import MIMEText

# -------------------------------
# Serial Communication with Arduinos
# -------------------------------
arduino_port = "COM6" #change depending on device (COM3 or 6)
baud_rate = 9600

try:
    arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
    print(f"Connected to Arduino on {arduino_port}")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    arduino = None

# Video file paths
video_file_1 = "D:/feeds/Scene2Cam1_trimmed.MOV"
video_file_2 = "D:/feeds/Scene2Cam2_trimmed.MOV"

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

# Email to SMS configuration
smtp_server = 'smtp.gmail.com'
smtp_port = 587
email_user = 'hebanemel@gmail.com'
email_password = 'jegl lojy wzcn pzil'  # Use an App Password if 2FA is enabled
sms_gateway = '3182684939@mms.att.net'  # ATT SMS gateway

def send_text_alert():
    """Sends a text message via email-to-SMS."""
    msg = MIMEText('🚨 Alert: Person detected in the blue zone!')
    msg['From'] = email_user
    msg['To'] = sms_gateway
    msg['Subject'] = 'Intrusion Alert'

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_user, sms_gateway, msg.as_string())
        server.quit()
        print('Text alert sent!')
    except Exception as e:
        print(f"Failed to send text: {e}")

# -------------------------------
# Virtual Zone Class with Independent Corner Dragging
# -------------------------------
# -------------------------------
# Fixed Virtual Zone Class (no dragging)
# -------------------------------
class VirtualZone:
    def __init__(self, corners, color=(0, 255, 0)):
        self.corners = corners
        self.color = color

    def draw(self, frame):
        for i in range(4):
            cv2.line(frame, self.corners[i], self.corners[(i + 1) % 4], self.color, 2)

    def is_inside(self, x, y):
        contour = np.array(self.corners, dtype=np.int32)
        return cv2.pointPolygonTest(contour, (x, y), False) >= 0

# -------------------------------
# Zone Initialization for Left and Right Halves
# -------------------------------
zone1_corners = [(0, 0), (FRAME_WIDTH // 2, 0), (FRAME_WIDTH // 2, FRAME_HEIGHT), (0, FRAME_HEIGHT)]       # Green Zone (Left)
zone2_corners = [(FRAME_WIDTH // 2, 0), (FRAME_WIDTH, 0), (FRAME_WIDTH, FRAME_HEIGHT), (FRAME_WIDTH // 2, FRAME_HEIGHT)]  # Blue Zone (Right)

zone1 = VirtualZone(zone1_corners, color=(0, 255, 0))   # Green (Left Half)
zone2 = VirtualZone(zone2_corners, color=(255, 0, 0))   # Blue (Right Half)



# Frame Capture Thread
def capture_frames(cap, queue, cam_id, fps):
    """Thread function to capture frames from video files."""
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Video {cam_id} ended.")
            break

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        if queue.full():
            queue.get()
        queue.put(frame)

        # Control frame rate based on FPS
        time.sleep(1 / fps)


# Distance Calculation Using Bounding Box Centers
def calculate_distance_from_disparity(disparity, focal_length, baseline):
    """Calculate distance using disparity."""
    if disparity == 0:  # Prevent division by zero
        return None
    distance = abs(-0.0008*disparity**3 + 0.0997*disparity**2 - 4.2073*disparity +73.5295)
    return distance

def non_max_suppression(boxes, iou_threshold=0.5):
    """Applies NMS to filter out overlapping boxes."""
    if len(boxes) == 0:
        return []

    boxes = sorted(boxes, key=lambda x: x[-1], reverse=True)  # Sort by confidence
    filtered = []

    while boxes:
        best = boxes.pop(0)
        filtered.append(best)

        boxes = [box for box in boxes if iou(box, best) < iou_threshold]

    return filtered


def iou(box1, box2):
    """Calculate IoU between two boxes (xyxy format)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union_area = box1_area + box2_area - inter_area
    return inter_area / union_area if union_area != 0 else 0


# Nearest Neighbor Matching for Accurate Pairing
def match_persons(results1, results2, confidence_threshold=0.5):
    def extract_and_filter(results):
        persons = [box.xyxy[0].tolist() + [box.conf[0].item()] for box in results.boxes 
                   if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold]
        return non_max_suppression(persons)

    persons1 = extract_and_filter(results1)
    persons2 = extract_and_filter(results2)

    pairs = []
    for p1 in persons1:
        x1 = (p1[0] + p1[2]) / 2
        y1 = (p1[1] + p1[3]) / 2

        if not persons2:
            print("No person detected in Camera 2 frame.")
            continue  # Skip this p1 if there's nothing to match it with

        distances = [math.hypot(x1 - (p2[0] + p2[2]) / 2, y1 - (p2[1] + p2[3]) / 2) for p2 in persons2]
        
        if len(distances) == 0:
            continue  # Additional safety
        
        min_idx = np.argmin(distances)
        pairs.append((p1, persons2[min_idx]))

    return pairs


# Video Initialization
cap1 = cv2.VideoCapture(video_file_1)
cap2 = cv2.VideoCapture(video_file_2)

if not cap1.isOpened() or not cap2.isOpened():
    print("Error: Could not open video files.")
    exit()

# Get FPS from video files
fps1 = cap1.get(cv2.CAP_PROP_FPS)
fps2 = cap2.get(cv2.CAP_PROP_FPS)
fps = min(fps1, fps2)  # Use the lower FPS to prevent desync
print(f"Video 1 FPS: {fps1}")
print(f"Video 2 FPS: {fps2}")
print(f"Using FPS: {fps}")

# Start frame capture threads
thread1 = threading.Thread(target=capture_frames, args=(cap1, queue1, 1, fps))
thread2 = threading.Thread(target=capture_frames, args=(cap2, queue2, 2, fps))
thread1.start()
thread2.start()

text_alert_sent = False
last_alert_time = 0
cooldown_duration = 10
# Display Loop with Combined Frames, Distance, and Disparity
while True:


    if not queue1.empty() and not queue2.empty():
        frame1 = queue1.get()
        frame2 = queue2.get()

        frame1 = cv2.resize(frame1, (FRAME_WIDTH, FRAME_HEIGHT))
        frame2 = cv2.resize(frame2, (FRAME_WIDTH, FRAME_HEIGHT))

        results1 = model.predict(frame1, verbose=False)[0]
        results2 = model.predict(frame2, verbose=False)[0]

        frame1_resized = results1.plot()
        frame2_resized = results2.plot()

        zone1.draw(frame1_resized)
        zone1.draw(frame2_resized)
        zone2.draw(frame1_resized)
        zone2.draw(frame2_resized)

        pairs = match_persons(results1, results2, confidence_threshold=0.5)

        intrusion_detected = False
        blue_zone_intrusion = False

        distances = []
        disparities = []
        centers = []
        prev_dists = {}

        disparity_history = {}
        frame_count = 10
        for i, (box1, box2) in enumerate(pairs):
            conf1 = box1[-1]
            conf2 = box2[-1]

            if conf1 < 0.5 or conf2 < 0.5:
                continue

            # Calculate disparity using average of left, right, and center x-coordinates
            left_disparity = abs(box1[0] - box2[0])
            right_disparity = abs(box1[2] - box2[2])
            center_disparity = abs((box1[0] + box1[2]) / 2 - (box2[0] + box2[2]) / 2)

            disparity = np.mean([left_disparity, right_disparity, center_disparity])

                # Store and average disparity across frames
            pair_id = f"{tuple(box1)}-{tuple(box2)}"
            if pair_id not in disparity_history:
                disparity_history[pair_id] = []
            disparity_history[pair_id].append(disparity)
            if len(disparity_history[pair_id]) > frame_count:
                disparity_history[pair_id].pop(0)

            # Calculate the smoothed disparity using the median
            smoothed_disparity = np.median(disparity_history[pair_id])
            # Calculate distance from disparity
            distance = calculate_distance_from_disparity(smoothed_disparity, focal_length, baseline)

            # Apply smoothing to distance
            if distance is not None:
                if pair_id in prev_dists:
                    prev_distance = prev_dists[pair_id]
                    distance = 0.7 * prev_distance + 0.3 * distance  # Apply smoothing (adjust coefficients as needed)

                prev_dists[pair_id] = distance


            if distance is not None:
                distances.append(distance)
                disparities.append(disparity)

                center_x1 = int((box1[0] + box1[2]) / 2)
                center_y1 = int((box1[1] + box1[3]) / 2)
                centers.append((center_x1, center_y1))

                color = (0, 0, 255) if distance <= 20 else (0, 255, 0)
                cv2.putText(frame1_resized, f"{distance:.2f} ft", (center_x1, center_y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.circle(frame1_resized, (center_x1, center_y1), 5, (255, 0, 0), -1)
                cv2.rectangle(frame1_resized, (int(box1[0]), int(box1[1])), (int(box1[2]), int(box1[3])), (0, 255, 0), 2)

                if distance <= 20 and zone1.is_inside(center_x1, center_y1):
                    intrusion_detected = True
                if distance <= 20 and zone2.is_inside(center_x1, center_y1):
                    blue_zone_intrusion = True

                if intrusion_detected and arduino:
                    print("Sending ALARM to Arduino")
                    arduino.write(b'ALARM\n')

        current_time = time.time()
        if blue_zone_intrusion and not text_alert_sent and (current_time - last_alert_time) > cooldown_duration:
            threading.Thread(target=send_text_alert).start()
            text_alert_sent = True
            last_alert_time = current_time
        elif not blue_zone_intrusion:
            text_alert_sent = False 

        combined_height = FRAME_HEIGHT + 300
        combined_frame = np.zeros((combined_height, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        combined_frame[:FRAME_HEIGHT, :FRAME_WIDTH] = frame1_resized
        combined_frame[:FRAME_HEIGHT, FRAME_WIDTH:] = frame2_resized

        for i, dist in enumerate(distances):
            cv2.putText(combined_frame, f"Person {i+1}: {dist:.2f} ft", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        for i, disparity in enumerate(disparities):
            cv2.putText(combined_frame, f"Disparity {i+1}: {disparity:.2f} px", (10, FRAME_HEIGHT + 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if intrusion_detected:
            cv2.putText(combined_frame, "Intrusion Detected!", (10, FRAME_HEIGHT + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("Combined Feed", combined_frame)

    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break



cap1.release()
cap2.release()
cv2.destroyAllWindows()