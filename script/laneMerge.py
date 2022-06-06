# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from time import sleep
from script.obu import OBU
from script.rsu import RSU
import geopy, threading
import geopy.distance

# Global variables
rsu_ip = "192.168.98.10"
obu_1_ip = "192.168.98.20"
obu_2_ip = "192.168.98.21"

# Coordinates RSU
rsu_coords = [40.640585, -8.663218]

# Coordinates of OBU_1's first position
obu_1_start = [40.640571, -8.663110]

# Coordinates of OBU_2's first position
obu_2_start = [40.640615, -8.662906]

# Speed values
speed = [60, 80, 100, 120, 140]

# Delta distance - the default move distance that a OBU mades 
delta_dist = 5

# Merge Location
merge_coords = [40.6402746, -8.6634728]

# Subscribe Topics
cam_subscribe_topic = "vanetza/out/cam"
denm_subscribe_topic = "vanetza/out/denm"
cpm_subscribe_topic = "vanetza/out/cpm"

# DENM "causeCodes" and "subCauseCodes"
causeCodes = {"Approaching Merge": 31, "Merge situation": 32, "Change position": 33, 
              "Reduce the speed": 34, "Increase the speed": 35, "Mantain speed": 36}

# The causeCode "Merge situation" has the following subCauseCodes
subCauseCodes = {"Wants to merge": 41, "Going to merge": 42, "Merge done": 43, "Abort merge": 44}

# ------------------------------------------ Lane Merge Class ---------------------------------------- 
class LaneMerge():
    OBUs: list
    rsu: RSU

    # The Lane Merge constructor
    def __init__(self):
        # Create the OBUs
        obu_1 = OBU(obu_1_ip, 1, obu_1_start, speed[1])
        obu_2 = OBU(obu_2_ip, 2, obu_2_start, speed[3])

        # Create the RSU
        self.rsu = RSU(rsu_ip, 3, rsu_coords)
        
        # An OBU list with all the OBUs created
        self.OBUs = []
        self.OBUs.append(obu_1)
        self.OBUs.append(obu_2)

    # To truncate an number with the number of decimals passed as argument
    def truncate(self, num, dec_plc):
        return int(num * 10**dec_plc) / 10**dec_plc

    # The brain of the Lane Merge class - the "main" method  
    def run(self):
        # Start the run routine of the subscribe method of every OBU and RSU
        for index in range(0, len(self.OBUs)):
            self.OBUs[index].start()
        self.rsu.start()

        i = 0
        while True:
            # TODO
            # OBUs can send CAM msgs untill 10 Hz 
            # RSUs only send CAM msgs at 1Hz frequency
            print("---------------------------------------------------------------------------------------------")
            
            for index in range(0, len(self.OBUs)):
                # If it's the OBU on the merge lane of the highway
                if(self.OBUs[index].id == 1):
                    if (i < 7):
                        pos = geopy.distance.geodesic(meters = delta_dist*i).destination(self.OBUs[index].start_pos, 222)
                        # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                        self.OBUs[index].updatePos([self.truncate(pos.latitude, 7), self.truncate(pos.longitude, 7)])
                    else:
                        pos = geopy.distance.geodesic(meters = delta_dist*i).destination(self.OBUs[index].start_pos, 223)
                        # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                        self.OBUs[index].updatePos([self.truncate(pos.latitude, 7), self.truncate(pos.longitude, 7)])
                    
                    self.OBUs[index].publish_CAM([pos.latitude, pos.longitude, self.OBUs[index].speed])
                # If it's an OBU on the main lane of the highway
                else:
                    pos = geopy.distance.geodesic(meters = delta_dist*i).destination(self.OBUs[index].start_pos, 225)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")        
                    self.OBUs[index].updatePos([self.truncate(pos.latitude, 7), self.truncate(pos.longitude, 7)])

                    self.OBUs[index].publish_CAM([pos.latitude, pos.longitude, self.OBUs[index].speed])

            # TODO - DENM msgs with a causeCode without a subCauseCode have the subCauseCode 
            #        equals to the causeCode 

            self.rsu.publish_CAM([rsu_coords[0], rsu_coords[1], 0])

            # To get the CAM and DENM msgs received by all the OBUs
            for num in range(0, len(self.OBUs)):
                if(len(self.OBUs[num].cam_queue) > 0):
                    for size in range (0, len(self.OBUs[num].cam_queue)):
                        print("OBU_"+str(self.OBUs[num].id)+" CAM received: "+str(self.OBUs[num].cam_queue[0]))
                        self.OBUs[num].popItemInCamQueue()

                if(len(self.OBUs[num].denm_queue) > 0):
                    print("OBU_"+str(self.OBUs[num].id)+" DENM received: "+str(self.OBUs[num].denm_queue[0]))
                    self.OBUs[num].popItemInDenmQueue()

            # RSU CAM and DENM msgs received
            if(len(self.rsu.cam_queue) > 0):
                print("RSU_"+str(self.rsu.id)+" CAM received: "+str(self.rsu.cam_queue))
                
                for size in range (0, len(self.rsu.cam_queue)):
                    msg = self.rsu.cam_queue[0]

                    # Unfactor the coordinates received
                    unfactor_coords = [msg["latitude"]/(10**7), msg["longitude"]/(10**7)]
                    # print(unfactor_coords)

                    # Last position before the merge point (merge_point - delta_dist)
                    approaching_merge = geopy.Point(merge_coords[0], merge_coords[1])
                    merge_dist = geopy.distance.geodesic(meters = -delta_dist).destination(approaching_merge, 223)
                    appr_merge_coords = [self.truncate(merge_dist.latitude, 7), 
                                         self.truncate(merge_dist.longitude, 7)]
                    
                    # There's a vehicle approaching the merge point
                    if((appr_merge_coords[0] == unfactor_coords[0]) and 
                        (appr_merge_coords[1] == unfactor_coords[1])):
                        print("OBU_"+str(msg["stationID"])+" is approaching the merge point")

                        self.rsu.publish_DENM([unfactor_coords[0], unfactor_coords[1], 
                                causeCodes["Approaching Merge"], causeCodes["Approaching Merge"]])

                    self.rsu.popItemInCamQueue()

            if(len(self.rsu.denm_queue) > 0):
                print("RSU_"+str(self.rsu.id)+" DENM received: "+str(self.rsu.denm_queue[0]))
                self.rsu.popItemInDenmQueue()

            sleep(1)
            i+=1

    # To get the actual status of the Lane Merge application
    def get_status(self):
        msg = {}
        for obu in self.OBUs:
            msg["OBU_"+str(obu.id)] = obu.obu_status()

        return msg

# ------------------------------------------ Main Function ---------------------------------------- 
if __name__ == '__main__':
    lane_merge = LaneMerge()
    lane_merge_thread = threading.Thread(target = lane_merge.run)
    lane_merge_thread.start()