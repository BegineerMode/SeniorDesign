
debug = False


class DistTracker:

    def __init__(self):
        self.detection = []

    def update(self, detections):
        if self.detection == []:
            self.detection = detections
            for objects in detections:
                pass
    
    


class Objects:

    def __init__(self, coordinates, ID) -> None:
        self.coordinates = coordinates
        self.ID = ID
    
    def update(self, coordinates):
        self.coordinates = coordinates

    def SameObjectDetection
        

if debug == True:
    tracker = DistTracker()
    print(tracker.detection)
    detection = [[1,2],[3,4]]
    tracker.update(detection)
    print(tracker.detection)


