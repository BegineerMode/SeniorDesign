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
import json

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
stream_url_1 = "http://192.168.1.134:8080"
stream_url_2 = "http://192.168.1.107:8080"


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

# Ground zone defined in real-world units (feet)
zone_polygon_ground = np.array([[0, 0], [6, 0], [6, 4], [0, 4]], dtype=np.float32)  # 6x4 feet zone

zone_red = np.array([[-3, 10], #bottom-left corner
                     [0, 10], #bottom-right corner
                     [0, 14], #top-right
                     [-3, 14]], #top-left
                     dtype=np.float32)     
zone_blue = np.array([[0, 10], #bottom-left
                      [3, 10], #bottom-right
                      [3, 14], #top-right
                      [0, 14]], #top-left
                      dtype=np.float32)   

zones = {
    "red": zone_red,
    "blue": zone_blue,
}

# Approximate projection constants (tune as needed)
fov_x_deg = 60  # horizontal field of view of camera
focal_length_px = 700  # assumed/calculated focal length in pixels
sensor_width_inches = 0.25  # typical Raspberry Pi camera sensor width
image_width_px = 640  # match your FRAME_WIDTH
camera_height_ft = 3.0

# Calculate degrees per pixel
fov_rad = np.deg2rad(fov_x_deg)
angle_per_pixel = fov_rad / image_width_px

# Define image center (assuming undistorted)
cx = image_width_px / 2


def approximate_ground_position(center_x, disparity):
    if disparity <= 0:
        return None

    # Estimate depth from disparity
    baseline_ft = 1.5  # 18 inches
    Z = (focal_length_px * baseline_ft) / disparity  # depth in feet

    # Horizontal angle from center
    angle = (center_x - cx) * angle_per_pixel
    X = Z * np.tan(angle)  # horizontal position relative to center

    return np.array([X, Z])  # ground point (X, Z)


def detect_zone_membership(ground_pt):
    for name, polygon in zones.items():
        if cv2.pointPolygonTest(polygon, tuple(ground_pt), False) >= 0:
            return name
    return None


def project_ground_to_image(X, Z):
    if Z <= 0:
        return None
    angle = np.arctan2(X, Z)
    x_pixel = int(cx + angle / angle_per_pixel)
    y_pixel = int(FRAME_HEIGHT - Z * 8)  # this makes further points higher up visually
    return (x_pixel, y_pixel)


# This replaces the homography-based method with a geometry-based projection using known FOV and disparity.
# It's easier for rapid deployment without requiring ground calibration.




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
    input_points = [6, 10, 15, 20, 25]         # Raw distances
    scale_factors = [1.49, 1.48, 1.46, 1.44, 1.43]
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
if fps1 == 0 or fps2 == 0:
    fps1 = fps2 = fps = 20.0  # or 15.0, depending on your stream
else:
    fps = min(fps1, fps2)

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
cooldown_duration = 30
red_zone_triggered = False 

# Inside your main while loop
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
        red_zone_triggered = False  # NEW: track if anyone is in the red zone
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

            left_disp = abs(box1[0] - box2[0])
            right_disp = abs(box1[2] - box2[2])
            center_disp = abs((box1[0] + box1[2]) / 2 - (box2[0] + box2[2]) / 2)
            disparity = np.median([left_disp, right_disp, center_disp])

            pair_key = f"{assigned_id}"
            if pair_key not in disparity_history:
                disparity_history[pair_key] = []
            disparity_history[pair_key].append(disparity)
            if len(disparity_history[pair_key]) > 10:
                disparity_history[pair_key].pop(0)

            if len(disparity_history[pair_key]) < 3:
                continue

            smoothed_disparity = np.median(disparity_history[pair_key])
            distance = calculate_distance_from_disparity(smoothed_disparity)
            approx_ground_pt = approximate_ground_position(center_x, smoothed_disparity)

            zone_name = None
            if approx_ground_pt is not None:
                zone_name = detect_zone_membership(approx_ground_pt)
                if zone_name:
                    intrusion_detected = True
                    if zone_name == "red":
                        red_zone_triggered = True  # ← mark red zone

            if distance is None:
                if height1 > 0:
                    distance = 2000 / height1
                else:
                    continue

            if height1 > 0:
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
            distance = distance * scale_factor
            distances.append(distance)
            disparities.append(smoothed_disparity)

            zone_colors = {
                "red": (0, 0, 255),
                "blue": (255, 0, 0),
            }
            zone_color = zone_colors.get(zone_name, (255, 255, 255))

            cv2.putText(frame1_resized, zone_name if zone_name else "no zone", (center_x, center_y + 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone_color, 1)

            cv2.putText(frame1_resized, f"Ground: ({approx_ground_pt[0]:.1f}, {approx_ground_pt[1]:.1f}) ft" if approx_ground_pt is not None else "Ground: N/A",
                        (center_x, center_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            color = (0, 0, 255) if distance <= 20 else (0, 255, 0)
            cv2.putText(frame1_resized, f"{distance:.2f} ft", (center_x, center_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.circle(frame1_resized, (center_x, center_y), 5, (255, 0, 0), -1)
            cv2.rectangle(frame1_resized, (int(box1[0]), int(box1[1])), (int(box1[2]), int(box1[3])), (0, 255, 0), 2)
            cv2.putText(frame1_resized, f"ID {assigned_id}", (center_x, center_y + 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 255), 1)

        id_memory = new_id_memory
        expired_ids = [pid for pid, t in id_timestamps.items() if current_time - t > id_timeout]
        for eid in expired_ids:
            id_timestamps.pop(eid, None)

        # Cooldown check for sending alert and Arduino signal
        if intrusion_detected and not text_alert_sent and (time.time() - last_alert_time) > cooldown_duration:
            #threading.Thread(target=send_text_alert).start()
            text_alert_sent = True
            last_alert_time = time.time()
            if arduino:
                try:
                    if red_zone_triggered:
                        arduino.write(b"RED_ON\n")
                    else:
                        arduino.write(b"RED_OFF\n")
                except Exception as e:
                    print(f"Failed to send to Arduino: {e}")

        elif not intrusion_detected:
            text_alert_sent = False

        # Visualization
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

        cv2.imshow("Combined Feed", combined_frame)

    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break

cap1.release()
cap2.release()
cv2.destroyAllWindows()

