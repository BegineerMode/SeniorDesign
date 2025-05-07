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
import socket, pickle, struct

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 9999))  # IP of GUI machine over WireGuard
conn = sock.makefile('wb')

import json

with open("ai_config.json", "r") as f:
    config = json.load(f)

camera1 = config.get("camera1")
camera2 = config.get("camera2")


print("finalCamera has start!")

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("10.0.0.2", 9998))
sock.sendall(b"AI process started successfully")
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
# stream_url_1 = "http://192.168.1.134:8080"
# stream_url_2 = "http://192.168.1.107:8080"
stream_url_1 = camera1
stream_url_2 = camera2

# Load YOLO model
model = YOLO('D:/runs/detect/train11/weights/last.pt')

# Camera parameters
focal_length = 700  # Focal length in pixels
baseline_in = 18   # Distance between cameras in meters

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
sms_gateway = '3189871267@mms.att.net'  # ATT SMS gateway

def send_text_alert():
    """Sends a text message via email-to-SMS and a regular email alert."""
    message_body = message_body = """
    A person was detected entering the restricted blue zone.

    Please review the security feed immediately.

    - Substation Intrusion Detection System
    This is an automated message do not reply.
        """

    # Create the message for SMS
    sms_msg = MIMEText(message_body)
    sms_msg['From'] = email_user
    sms_msg['To'] = sms_gateway
    sms_msg['Subject'] = 'Intrusion Alert'

    # Create the message for regular email
    email_msg = MIMEText(message_body)
    email_msg['From'] = email_user
    email_msg['To'] = 'ethanlsu@gmail.com'  
    email_msg['Subject'] = 'Intrusion Alert - Email'

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)

        # Send SMS
        server.sendmail(email_user, sms_gateway, sms_msg.as_string())

        # Send Email
        server.sendmail(email_user, 'ethanlsu@gmail.com', email_msg.as_string())

        server.quit()
        print('Text and Email alerts sent!')
    except Exception as e:
         print(f"Failed to send alert: {e}")


# -------------------------------
# Virtual Zone Class with Independent Corner Dragging
# -------------------------------
# -------------------------------
# Fixed Virtual Zone Class (no dragging)
# -------------------------------
# Define world-coordinate zones (in feet)
zone_red = np.array([[-3, 10], [3, 10], [3, 14], [-3, 14]], dtype=np.float32)
zone_blue = np.array([[-3, 14], [3, 14], [3, 18], [-3, 18]], dtype=np.float32)

zones = {
    "red": zone_red,
    "blue": zone_blue,
}

# Helper to check if real-world (x, y) is inside a zone
def is_point_in_zone(xy_point, zone_polygon):
    """Check if a (x, y) world-coordinate point is inside a zone polygon."""
    zone_int = np.array(zone_polygon, dtype=np.int32)
    return cv2.pointPolygonTest(zone_int, (int(xy_point[0]), int(xy_point[1])), False) >= 0




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
def calculate_distance_from_disparity(disparity):
    """
    Calculates distance (in feet) from disparity (in pixels) based on an inverse fit.
    Tuned for 18-inch baseline, Arducam OV5647 stereo cameras.
    """
    if disparity <= 0:
        return None  # Prevent division by zero or negative disparities
    
    # # Updated inverse model

    # if disparity > 21.1:
    #     # Close range formula (5-20 ft)
    #     A = 448.77
    #     B = 0.53
    #     distance_ft = A / (disparity + B)

    # elif 18 < disparity <= 21.1:
    #     # Medium range formula ( 25 ft)
    #     A = 520
    #     B = 0.4
    #     distance_ft = A / (disparity + B)

    # else:
    #     # Far range formula (30 ft)
    #     A = 775.5  10 13 17
    #     B = 9.24
    #     distance_ft = A / (disparity + B)
    baseline = baseline_in * 0.0254
    distance = (focal_length*baseline)/disparity
    input_points = [10, 15, 20, 25, 30]         # Raw distances
    scale_factors = [0.9901, 1.0791, 1.1429, 1.24, 1.4]
    offsets =      [-0.3, -0.3, -0.4, -0.5, -0.6]
    scale = np.interp(distance, input_points, scale_factors)
    offset = np.interp(distance, input_points, offsets)
    corrected = distance * scale + offset
    return corrected


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
    def extract_people(results):
        return [
            box.xyxy[0].tolist() + [box.conf[0].item()]
            for box in results.boxes
            if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold
        ]

    persons1 = extract_people(results1)
    persons2 = extract_people(results2)

    if not persons1 or not persons2:
        return []

    matched_pairs = []
    used_indices = set()

    for p1 in persons1:
        x1c = (p1[0] + p1[2]) / 2
        y1c = (p1[1] + p1[3]) / 2
        h1 = p1[3] - p1[1]

        best_idx = -1
        best_score = float('inf')

        for idx, p2 in enumerate(persons2):
            if idx in used_indices:
                continue

            x2c = (p2[0] + p2[2]) / 2
            y2c = (p2[1] + p2[3]) / 2
            h2 = p2[3] - p2[1]

            center_dist = math.hypot(x1c - x2c, y1c - y2c)
            height_diff = abs(h1 - h2)

            score = center_dist + height_diff * 2  # Weight height difference

            if score < best_score:
                best_score = score
                best_idx = idx

        if best_idx != -1:
            matched_pairs.append((p1, persons2[best_idx]))
            used_indices.add(best_idx)

    return matched_pairs



# Video Initialization
cap1 = cv2.VideoCapture(stream_url_1)
cap2 = cv2.VideoCapture(stream_url_2)

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

# Display Loop with Combined Frames, Distance, and Disparity
# Tracking dictionaries before loop
next_id = 0
id_memory = {}  # {id: (center_x, center_y)}
id_timestamps = {}
id_timeout = 1.0
prev_dists = {}
disparity_history = {}
frame_count = 10
text_alert_sent = False
last_alert_time = 0
cooldown_duration = 10

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

        pairs = match_persons(results1, results2, confidence_threshold=0.5)

        intrusion_detected = False
        blue_zone_intrusion = False
        distances = []
        disparities = []
        new_id_memory = {}
        current_time = time.time()

        for i, (box1, box2) in enumerate(pairs):
            conf1 = box1[-1]
            conf2 = box2[-1]
            if conf1 < 0.5 or conf2 < 0.5:
                continue

            height1 = box1[3] - box1[1]
            height2 = box2[3] - box2[1]
            if abs(height1 - height2) > 50:
                continue

            center_x = int((box1[0] + box1[2]) / 2)
            center_y = int((box1[1] + box1[3]) / 2)

            # Assign persistent ID
            assigned_id = None
            min_dist = float('inf')
            for pid, (prev_x, prev_y, prev_height) in id_memory.items():
                if current_time - id_timestamps.get(pid, 0) > id_timeout:
                    continue
                dist = math.hypot(center_x - prev_x, center_y - prev_y)
                height_diff = abs(height1 - prev_height)
                if dist < 60 and height_diff < 30 and dist < min_dist:
                    assigned_id = pid
                    min_dist = dist

            if assigned_id is None:
                assigned_id = next_id
                next_id += 1

            new_id_memory[assigned_id] = (center_x, center_y, height1)
            id_timestamps[assigned_id] = current_time

            # Calculate disparity
            left_disp = abs(box1[0] - box2[0])
            right_disp = abs(box1[2] - box2[2])
            center_disp = abs((box1[0] + box1[2]) / 2 - (box2[0] + box2[2]) / 2)
            disparity = np.median([left_disp, right_disp, center_disp])

            pair_key = f"{assigned_id}"
            disparity_history.setdefault(pair_key, []).append(disparity)
            if len(disparity_history[pair_key]) > 10:
                disparity_history[pair_key].pop(0)

            if len(disparity_history[pair_key]) < 3:
                continue

            smoothed_disparity = np.median(disparity_history[pair_key])
            distance = calculate_distance_from_disparity(smoothed_disparity)

            if distance is None:
                if height1 > 0:
                    distance = 2000 / height1
                else:
                    continue

            pixel_estimate = 2000 / height1
            distance = 0.6 * distance + 0.4 * pixel_estimate

            if height1 < 100:
                distance *= 0.9
            elif height1 > 250:
                distance *= 1.05

            if pair_key in prev_dists:
                prev_distance = prev_dists[pair_key]
                if abs(prev_distance - distance) > 5:
                    distance = prev_distance
                else:
                    distance = 0.8 * prev_distance + 0.2 * distance
            prev_dists[pair_key] = distance

            scale_factor = 2.0
            distance *= scale_factor
            distances.append(distance)
            disparities.append(smoothed_disparity)

            # Convert to real-world point
            horizontal_fov = 70
            angle_from_center = (center_x - FRAME_WIDTH / 2) / (FRAME_WIDTH / 2) * (horizontal_fov / 2)
            x_world = math.tan(math.radians(angle_from_center)) * distance
            y_world = distance
            point_world = (x_world, y_world)

            # Zone checks
            zone_label = "None"
            zone_color = (200, 200, 200)

            if is_point_in_zone(point_world, zones["red"]):
                zone_label = "Red Zone"
                zone_color = (0, 0, 255)
                intrusion_detected = True
                sock.sendall(b"Alarm")

            elif is_point_in_zone(point_world, zones["blue"]):
                zone_label = "Blue Zone"
                zone_color = (255, 0, 0)
                blue_zone_intrusion = True

            # Drawing
            cv2.putText(frame1_resized, f"{distance:.2f} ft", (center_x, center_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(frame1_resized, (center_x, center_y), 5, (255, 0, 0), -1)
            cv2.rectangle(frame1_resized, (int(box1[0]), int(box1[1])), (int(box1[2]), int(box1[3])), (0, 255, 0), 2)
            cv2.putText(frame1_resized, f"ID {assigned_id}", (center_x, center_y + 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 255), 1)
            cv2.putText(frame1_resized, f"{zone_label}", (center_x, center_y + 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone_color, 1)

        # After loop: turn off alarm if no red zone intrusion
        if not intrusion_detected:
            sock.sendall(b"Stop")

        # Cleanup expired IDs
        id_memory = new_id_memory
        expired_ids = [pid for pid, t in id_timestamps.items() if current_time - t > id_timeout]
        for eid in expired_ids:
            id_timestamps.pop(eid, None)

        # Text/email alert for blue zone
        if blue_zone_intrusion and not text_alert_sent and (time.time() - last_alert_time) > cooldown_duration:
            threading.Thread(target=send_text_alert).start()
            text_alert_sent = True
            last_alert_time = time.time()
        elif not blue_zone_intrusion:
            text_alert_sent = False

        # Final output
        combined_height = FRAME_HEIGHT + 300
        combined_frame = np.zeros((combined_height, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        combined_frame[:FRAME_HEIGHT, :FRAME_WIDTH] = frame1_resized
        combined_frame[:FRAME_HEIGHT, FRAME_WIDTH:] = frame2_resized

        for i, dist in enumerate(distances):
            cv2.putText(combined_frame, f"Person {i+1}: {dist:.2f} ft", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        for i, disp in enumerate(disparities):
            cv2.putText(combined_frame, f"Disparity {i+1}: {disp:.2f} px", (10, FRAME_HEIGHT + 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if intrusion_detected:
            cv2.putText(combined_frame, "Intrusion Detected!", (10, FRAME_HEIGHT + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        data = pickle.dumps(combined_frame)
        size = struct.pack(">L", len(data))
        conn.write(size + data)
        conn.flush()

    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break

cap1.release()
cap2.release()
cv2.destroyAllWindows()
