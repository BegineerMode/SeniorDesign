
debug = True
testing = False
dist = 25

class DistTracker:

    def __init__(self):
        self.detection = []
        self.objects = []

    def update(self, detections):
        if self.detection == []:
            self.detection = detections
        for coords in detections:
            self.CheckObject(coords)
        self.mergeConnectedObjects()
    
    def mergeConnectedObjects(self):
        for object1 in self.objects:
            for object2 in self.objects:
                Same = False
                if object1 != object2:
                    Same = self.SameObjectDetection(object2.coordinates, object1)
                if Same:
                    self.objects.remove(object2)
        count = 1
        for object in self.objects:
            object.ID = count
            count+=1


    def CheckObject(self, coordinates):
        Found = False
        totalObjects = 0
        for known in self.objects:
            if testing == True:
                print(known.ID ,known.coordinates, coordinates)
            totalObjects+=1
            Found = Found | self.SameObjectDetection(coordinates,known)
        if Found == False:
            newobject = Objects(coordinates, totalObjects+1)
            self.objects.append(newobject)
            if testing == True:
                print("New")
                print(newobject.coordinates)
            

    def SameObjectDetection(self, new, old):
        if (abs(new[0] - old.coordinates[0]) < dist and abs(new[1] - old.coordinates[1]) < dist):
            if testing == True:
                print(old.coordinates, new)
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
    detection = [[740, 315, 16, 17], [786, 310, 32, 29], [724, 308, 10, 14], [552, 266, 26, 26], [450, 247, 28, 49], [256, 244, 67, 22], [566, 235, 38, 19]]
    tracker.update(detection)
    for object in tracker.objects:
        print(object.ID, object.coordinates)
    testing = False
    print()
    detection = [[742, 317, 18, 15], [788, 311, 31, 29], [552, 266, 28, 26], [452, 247, 25, 49], [259, 244, 69, 20], [567, 234, 40, 20]]
    tracker.update(detection)
    for object in tracker.objects:
        print(object.ID, object.coordinates)

    
