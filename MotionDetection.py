# Code for Motion Detection

import cv2



Debug = False

# Create a VideoCapture object and read from input file
cap = cv2.VideoCapture('C:/Users/reese/Downloads/coffee.mp4', )

objdetect = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16)


# Check if camera opened successfully
if (cap.isOpened()== False):
    print("Error opening video file")

# Read until video is completed
while(cap.isOpened()):
    
# Capture frame-by-frame
    ret, frame = cap.read()
    if ret == True:

        mask = objdetect.apply(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area>20000:

                #cv2.drawContours(frame, [cnt], -1, (0,255,0), 2)
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0))

    # Display the resulting frame
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
