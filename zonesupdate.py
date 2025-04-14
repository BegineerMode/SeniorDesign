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
class VirtualZone:
    def __init__(self, x, y, w, h, color=(0, 255, 0)):
        self.corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        self.dragging_corner = None
        self.corner_size = 10
        self.color = color

    def draw(self, frame):
        for i in range(4):
            cv2.line(frame, self.corners[i], self.corners[(i + 1) % 4], self.color, 2)
            cv2.circle(frame, self.corners[i], self.corner_size, (0, 0, 255), -1)

    def handle_mouse_event(self, event, x, y):
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
        contour = np.array(self.corners, dtype=np.int32)
        return cv2.pointPolygonTest(contour, (x, y), False) >= 0


# Initialize virtual zone
zone1 = VirtualZone(100, 100, 200, 150, color=(0, 255, 0))   # Green
zone2 = VirtualZone(400, 100, 200, 150, color=(255, 0, 0))   # Blue

# Mouse event callback handles both zones
def mouse_callback(event, x, y, flags, param):
    zone1.handle_mouse_event(event, x, y)
    zone2.handle_mouse_event(event, x, y)

cv2.namedWindow("Combined Feed")
cv2.setMouseCallback("Combined Feed", mouse_callback)


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



# Nearest Neighbor Matching for Accurate Pairing
def match_persons(results1, results2, confidence_threshold=0.5):
    """Match persons across both frames using nearest neighbors."""
    # Extract bounding boxes that are labeled as 'person' (class 0) with confidence above the threshold
    persons1 = [box.xyxy[0].tolist() for box in results1.boxes if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold]
    persons2 = [box.xyxy[0].tolist() for box in results2.boxes if int(box.cls[0]) == 0 and box.conf[0] >= confidence_threshold]

    if not persons1 or not persons2:
        return []

    pairs = []
    if not persons1 or not persons2:
        return pairs
    
    for p1 in persons1:
        distances = [abs((p1[0] + p1[2]) / 2 - (p2[0] + p2[2]) / 2) for p2 in persons2]
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


# Display Loop with Combined Frames, Distance, and Disparity
while True:
    if not queue1.empty() and not queue2.empty():
        frame1 = queue1.get()
        frame2 = queue2.get()

        # YOLO Inference
        results1 = model.predict(frame1, verbose=False)[0]
        results2 = model.predict(frame2, verbose=False)[0]

        frame1_resized = results1.plot()
        frame2_resized = results2.plot()

        
        zone1.draw(frame1_resized)
        zone1.draw(frame2_resized)
        zone2.draw(frame1_resized)
        zone2.draw(frame2_resized)

        # Match persons across both frames
        pairs = match_persons(results1, results2, confidence_threshold=0.45)

        #flags
        intrusion_detected = False
        blue_zone_intrusion = False
        text_alert_sent = False

        distances = []
        disparities = []
        centers = []  # Store center points for display

        for box1, box2 in pairs:
            # Extract confidence scores correctly
            conf1 = box1[-1]  # YOLO box confidence
            conf2 = box2[-1]  # YOLO box confidence

            # Only process bounding boxes with a confidence greater than 0.5
            if conf1 < 0.5 or conf2 < 0.5:
                continue

            # Calculate disparity (absolute horizontal difference)
            disparity = abs((box1[0] + box1[2]) / 2 - (box2[0] + box2[2]) / 2)
            
            # Calculate distance from disparity
            distance = calculate_distance_from_disparity(disparity, focal_length, baseline)

            if distance is not None:
                distances.append(distance)
                disparities.append(disparity)

                #  Calculate center coordinates of the bounding boxes
                center_x1 = int((box1[0] + box1[2]) / 2)
                center_y1 = int((box1[1] + box1[3]) / 2)

                # Store center points for display
                centers.append((center_x1, center_y1))

                # Draw distance text on the frame
                color = (0, 0, 255) if distance <=20 else (0, 255, 0)  # Red for intrusion, green otherwise
                cv2.putText(frame1_resized, f"{distance:.2f} ft", (center_x1, center_y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                #  Draw center point coordinates
                #cv2.putText(frame1_resized, f"({center_x1}, {center_y1})", 
                 #           (center_x1 + 10, center_y1 + 10), 
                  #          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

                # Draw the center point of the bounding box (blue circle)
                cv2.circle(frame1_resized, (center_x1, center_y1), 5, (255, 0, 0), -1)

                # Draw the bounding box
                cv2.rectangle(frame1_resized, (int(box1[0]), int(box1[1])),
                              (int(box1[2]), int(box1[3])), (0, 255, 0), 2)

                # Trigger intrusion detection if conditions are met
                if distance <= 20 and zone1.is_inside(center_x1, center_y1):
                    intrusion_detected = True

                if distance <= 20 and zone2.is_inside(center_x1, center_y1):
                    blue_zone_intrusion = True

        # Trigger Arduino alarm if intrusion is detected
        if intrusion_detected and arduino:
            arduino.write(b'ALARM\n')

        # Trigger text message if blue zone is breached
        if blue_zone_intrusion and not text_alert_sent:
            send_text_alert()
            text_alert_sent = True

        # Combine frames for display
        combined_height = FRAME_HEIGHT + 300
        combined_frame = np.zeros((combined_height, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        combined_frame[:FRAME_HEIGHT, :FRAME_WIDTH] = frame1_resized
        combined_frame[:FRAME_HEIGHT, FRAME_WIDTH:] = frame2_resized

        # Display distance, disparity, and center point info
        for i, dist in enumerate(distances):
            cv2.putText(combined_frame, f"Person {i+1}: {dist:.2f} ft", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        for i, disparity in enumerate(disparities):
            cv2.putText(combined_frame, f"Disparity {i+1}: {disparity:.2f} px", (10, FRAME_HEIGHT + 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        #  Display center point coordinates
        #for i, (cx, cy) in enumerate(centers):
         #   cv2.putText(combined_frame, f"Center {i+1}: ({cx}, {cy})", 
          #              (10, FRAME_HEIGHT + 90 + i * 30),
           #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        #  Display "Intrusion Detected" message
        if intrusion_detected:
            cv2.putText(combined_frame, "Intrusion Detected!", (10, FRAME_HEIGHT + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # Show the combined feed
        cv2.imshow("Combined Feed", combined_frame)

    # Use FPS to slow down video playback
    key = cv2.waitKey(int(1000 / fps))  # This will slow down based on the FPS of the video
    if key & 0xFF == ord('q'):
        break


cap1.release()
cap2.release()
cv2.destroyAllWindows()









