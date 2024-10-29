# Code for Motion Detection

import cv2

#from ObjectTracker import *


Debug = False

# Create a VideoCapture object and read from input file
cap = cv2.VideoCapture('cars2.mp4', )

objdetect = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=16)


# Check if camera opened successfully
if (cap.isOpened()== False):
    print("Error opening video file")

# Read until video is completed
while(cap.isOpened()):
    
# Capture frame-by-frame
    ret, frame = cap.read()
    if ret == True:

        mask = objdetect.apply(frame)
        _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area>30:

                #cv2.drawContours(frame, [cnt], -1, (0,255,0), 2)
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0))
                
                detections.append([x, y, w, h])

    # Display the resulting frame
        print(detections)
        cv2.imshow('Frame', frame)
        
        
    # Press Q on keyboard to exit
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

# Break the loop
    else:
        break

# When everything done, release
# the video capture object
cap.release()

# Closes all the frames
cv2.destroyAllWindows()
