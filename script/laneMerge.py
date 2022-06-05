# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

import threading
from time import sleep
from obu import *
from rsu import *
import geopy
import geopy.distance

# Global variables
rsu_ip = "192.168.98.10"
obu_1_ip = "192.168.98.20"
obu_2_ip = "192.168.98.21"

# Coordinates RSU
rsu_coords = [40.640455, -8.663244]

# Coordinates of OBU_1's first position
obu_1_start = [40.640571, -8.663110]

# Coordinates of OBU_2's first position
obu_2_start = [40.640615, -8.662906]

# Speed values
speed = [60, 80, 100, 120, 140]

# Subscribe Topics
cam_subscribe_topic = "vanetza/out/cam"
denm_subscribe_topic = "vanetza/out/denm"
cpm_subscribe_topic = "vanetza/out/cpm"

# DENM "causeCodes" and "subCauseCodes"
causeCodes = {"Merge situation": 31, "Change position": 32, "Reduce the speed": 33, 
              "Increase the speed": 34, "Mantain speed": 35}

# The causeCode "Merge situation" has the following subCauseCodes
subCauseCodes = {"Wants to merge": 41, "Going to merge": 42, "Merge done": 43, 
                 "Abort merge": 44}

# ------------------------------------------ Main Function ---------------------------------------- 
if __name__ == '__main__':
    # Create the OBUs
    obu_1 = OBU(obu_1_ip, 1)
    obu_2 = OBU(obu_2_ip, 2)

    # Create the RSU
    rsu_1 = RSU(rsu_ip, 3)
    
    # Create the start postion of every OBU
    start_obu_1 = geopy.Point(obu_1_start[0], obu_1_start[1])
    start_obu_2 = geopy.Point(obu_2_start[0], obu_2_start[1])

    # Start the run routine of the subscribe method of every OBU and RSU
    obu_1.start()
    obu_2.start()
    # rsu_1.start()
    
    i = 0
    while True:
        if (i < 7):
            pos_obu_1 = geopy.distance.geodesic(meters = 5*i).destination(start_obu_1, 222)
            # print("["+str(d.latitude)+", "+str(d.longitude)+"],")
        else:
            pos_obu_1 = geopy.distance.geodesic(meters = 5*i).destination(start_obu_1, 223)
            # print("["+str(d.latitude)+", "+str(d.longitude)+"],")

        # obu_1.publish_CAM([pos_obu_1.latitude, pos_obu_1.longitude, speed[1]])
        
        # TODO - DENM msgs with a causeCode without a subCauseCode have the subCauseCode 
        #        equals to the causeCode 
        obu_1.publish_DENM([40.640551, -8.663130, causeCodes["Merge situation"], 
                            subCauseCodes["Wants to merge"]])

        pos_obu_2 = geopy.distance.geodesic(meters=5*i).destination(start_obu_2, 225)
        # print("["+str(pos_obu_2.latitude)+", "+str(pos_obu_2.longitude)+"],")        

        # obu_2.publish_CAM([pos_obu_2.latitude, pos_obu_2.longitude, speed[3]])

        # OBUs can send CAM msgs untill 10 Hz 
        # RSUs only send CAM msgs at 1Hz frequency

        # rsu_1.publish_CAM([rsu_coords[0], rsu_coords[1], 0])

        if(len(obu_2.cam_queue) > 0):
            print(obu_2.cam_queue[0])
            obu_2.popItemInCamQueue()
        
        if(len(obu_2.denm_queue) > 0):
            print(obu_2.denm_queue[0])
            obu_2.popItemInDenmQueue()

        sleep(1)
        i+=1