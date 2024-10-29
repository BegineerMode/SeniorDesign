
debug = True


class DistTracker:

    def __init__(self):
        self.detection = []
        self.objects = []

    def update(self, detections):
        if self.detection == []:
            self.detection = detections
        for coords in detection:
            self.CheckObject(coords)

    def CheckObject(self, coordinates):
        if self.objects == []:
            newobject = Objects(coordinates, 1)
            self.objects.append(newobject)
        else:
            Found = False
            totalObjects = 0
            for known in self.objects:
                totalObjects+=1
                Found = Found | self.SameObjectDetection(coordinates,known)
            if Found == False:
                newobject = Objects(coordinates, totalObjects+1)
                self.objects.append(newobject)
                

    def SameObjectDetection(self, new, old):
        if (abs(new[0] - old.coordinates[0]) < 10 and abs(new[1] - old.coordinates[1]) < 10):
            old.coordinates = new
            return True
        return False

class Objects:

    def __init__(self, coordinates, ID) -> None:
        self.coordinates = coordinates
        self.ID = ID

    def update(self, coordinates):
        self.coordinates = coordinates

if debug == True:
    tracker = DistTracker()
    detection = [[25,2]]
    tracker.update(detection)
    detection = [[13,8],[100,200]]
    tracker.update(detection)
    for object in tracker.objects:
        print(object.ID, object.coordinates)

    
