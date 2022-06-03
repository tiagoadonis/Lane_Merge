# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

import threading
from time import sleep
from obu import *
from rsu import *
from decimal import *

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

# Subscribe Topics
cam_subscribe_topic = "vanetza/out/cam"
denm_subscribe_topic = "vanetza/out/denm"
cpm_subscribe_topic = "vanetza/out/cpm"

# DENM "causeCodes" and "subCauseCodes"
causeCodes = {"Merge situation": "31", "Change position": "32", "Reduce the speed": "33", 
              "Increase the speed": "34", "Mantain speed": "35"}

# The causeCode "Merge situation" has the following subCauseCodes
subCauseCodes = {"Wants to merge": "41", "Going to merge": "42", "Merge done": "43", 
                 "Abort merge": "44"}

# ------------------------------------------ Main Function ---------------------------------------- 
if __name__ == '__main__':
    getcontext().prec = 8

    obu_1 = OBU(obu_1_ip, 1)
    # obu_1.publish_CAM([40.640551, -8.663130, 80])
    # obu_1.publish_DENM([40.640551, -8.663130, int(causeCodes["Merge situation"]), 
    #                     int(subCauseCodes["Wants to merge"])])
    # obu_1.subscribe(cam_subscribe_topic)

    obu_2 = OBU(obu_2_ip, 2)
    # obu_2.publish_CAM([40.640540, -8.663009, 120])
    # TODO -> what we pass as "subCauseCode" in a "causeCode" without "subCauseCode"? -> ficar igual ao cause code

    # obu_2.publish_DENM([40.640540, -8.663009, int(causeCodes["Change position"]), 0])

    rsu_1 = RSU(rsu_ip, 3)
    # rsu_1.publish_CAM([40.640455, -8.663244, 0])
    # Shares the obu_1 intention of merge
    # rsu_1.publish_DENM([40.640455, -8.663244, int(causeCodes["Merge situation"]), 
    #                     int(subCauseCodes["Abort merge"])])

    i = 0
    obu_1.start()
    obu_2.start()
    #rsu_1.start()

    while True:
        # TODO OBU_1 coords is okay -> coordenadas com metros (geopy.distance)
        obu_1_coords = [Decimal(obu_1_start[0]) - Decimal(0.0000232*i), 
                        Decimal(obu_1_start[1]) - Decimal(0.0000285*i)]

        # print("["+str(obu_1_coords[0])+", "+str(obu_1_coords[1])+"], ")
        obu_1.publish_CAM([float(obu_1_coords[0]), float(obu_1_coords[1]), 80])
        
        rsu_1.publish_CAM([rsu_coords[0], rsu_coords[1], 0])
        
        obu_2_coords = [Decimal(obu_2_start[0]) - Decimal(0.0000232*i), 
                        Decimal(obu_2_start[1]) - Decimal(0.0000485*i)]
        # print("["+str(obu_2_coords[0])+", "+str(obu_2_coords[1])+"], ")
        # obu_2.publish_CAM([float(obu_2_coords[0]), float(obu_2_coords[1]), 120])

        # OBUs and RSU publish CAMs at 1Hz = 1s frequency
        # OBUs até 10 Hz RSU 1Hz
        sleep(1)
        i+=1