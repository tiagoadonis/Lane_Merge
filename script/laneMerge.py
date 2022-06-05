# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from time import sleep
from obu import *
from rsu import *
import geopy, threading, math
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

# ------------------------------------------ Auxiliary Function ---------------------------------------- 
def truncate(num, dec_plc):
    return int(num * 10**dec_plc) / 10**dec_plc

# ------------------------------------------ Main Function ---------------------------------------- 
if __name__ == '__main__':
    # Create the OBUs
    obu_1 = OBU(obu_1_ip, 1)
    obu_2 = OBU(obu_2_ip, 2)

    # Create the RSU
    rsu_1 = RSU(rsu_ip, 3)
    
    # An OBU list with all the OBUs created
    OBUs = []
    OBUs.append(obu_1)
    OBUs.append(obu_2)

    # Create the start postion of every OBU
    start_obu_1 = geopy.Point(obu_1_start[0], obu_1_start[1])
    start_obu_2 = geopy.Point(obu_2_start[0], obu_2_start[1])

    # Start the run routine of the subscribe method of every OBU and RSU
    obu_1.start()
    obu_2.start()
    rsu_1.start()
    
    i = 0
    while True:
        # TODO
        # OBUs can send CAM msgs untill 10 Hz 
        # RSUs only send CAM msgs at 1Hz frequency

        print("--------------------------------------------------------------------------")
        if (i < 7):
            pos_obu_1 = geopy.distance.geodesic(meters = delta_dist*i).destination(start_obu_1, 222)
            # print("["+str(pos_obu_1.latitude)+", "+str(pos_obu_1.longitude)+"],")
        else:
            pos_obu_1 = geopy.distance.geodesic(meters = delta_dist*i).destination(start_obu_1, 223)
            # print("["+str(pos_obu_1.latitude)+", "+str(pos_obu_1.longitude)+"],")

        obu_1.publish_CAM([pos_obu_1.latitude, pos_obu_1.longitude, speed[1]])
        
        # TODO - DENM msgs with a causeCode without a subCauseCode have the subCauseCode 
        #        equals to the causeCode 

        pos_obu_2 = geopy.distance.geodesic(meters = delta_dist*i).destination(start_obu_2, 225)
        # print("["+str(pos_obu_2.latitude)+", "+str(pos_obu_2.longitude)+"],")        

        obu_2.publish_CAM([pos_obu_2.latitude, pos_obu_2.longitude, speed[3]])

        #rsu_1.publish_CAM([rsu_coords[0], rsu_coords[1], 0])

        # To get the CAM and DENM msgs received by all the OBUs
        for num in range(0, len(OBUs)):
            if(len(OBUs[num].cam_queue) > 0):
                # print("OBU_"+str(OBUs[num].id)+" CAM received: "+str(OBUs[num].cam_queue[0]))
                OBUs[num].popItemInCamQueue()

            if(len(OBUs[num].denm_queue) > 0):
                print("OBU_"+str(OBUs[num].id)+" DENM received: "+str(OBUs[num].denm_queue[0]))
                OBUs[num].popItemInDenmQueue()

        # RSU CAM and DENM msgs received
        if(len(rsu_1.cam_queue) > 0):
            print("RSU_"+str(rsu_1.id)+" CAM received: "+str(rsu_1.cam_queue))
            
            for size in range (0, len(rsu_1.cam_queue)):
                msg = rsu_1.cam_queue[0]

                # Unfactor the coordinates received
                unfactor_coords = [msg["latitude"]/(10**7), msg["longitude"]/(10**7)]
                # print(unfactor_coords)

                # Last position before the merge point (merge_point - delta_dist)
                approaching_merge = geopy.Point(merge_coords[0], merge_coords[1])
                merge_dist = geopy.distance.geodesic(meters = -delta_dist).destination(approaching_merge, 223)
                appr_merge_coords = [truncate(merge_dist.latitude, 7), truncate(merge_dist.longitude, 7)]
                
                # There's a vehicle approaching the merge point
                if((appr_merge_coords[0] == unfactor_coords[0]) and (appr_merge_coords[1] == unfactor_coords[1])):
                    print("OBU_"+str(msg["stationID"])+" is approaching the merge point")

                    rsu_1.publish_DENM([unfactor_coords[0], unfactor_coords[1], 
                            causeCodes["Approaching Merge"], causeCodes["Approaching Merge"]])

                rsu_1.popItemInCamQueue()

        if(len(rsu_1.denm_queue) > 0):
            print("RSU_"+str(rsu_1.id)+" DENM received: "+str(rsu_1.denm_queue[0]))
            rsu_1.popItemInDenmQueue()

        sleep(1)
        i+=1