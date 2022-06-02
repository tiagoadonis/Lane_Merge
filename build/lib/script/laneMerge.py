# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from obu import *
from rsu import *

# Global variables
rsu_ip = "192.168.98.10"
obu_1_ip = "192.168.98.20"
obu_2_ip = "192.168.98.21"

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
    obu_1 = OBU(obu_1_ip, 1)
    obu_1.publish_CAM([40.640551, -8.663130, 80])
    # obu_1.publish_DENM([40.640551, -8.663130, int(causeCodes["Merge situation"]), 
    #                    int(subCauseCodes["Wants to merge"])])
    # obu_1.subscribe(cam_subscribe_topic)

    obu_2 = OBU(obu_2_ip, 2)
    obu_2.publish_CAM([40.640540, -8.663009, 120])
    # TODO -> what we pass as "subCauseCode" in a "causeCode" without "subCauseCode"?
    # obu_2.publish_DENM([40.640540, -8.663009, int(causeCodes["Change position"]), 
    #                    int(subCauseCodes["Wants to merge"])])

    rsu_1 = RSU(rsu_ip, 3)
    # Shares the obu_1 intention of merge
    rsu_1.publish_DENM([40.640551, -8.663130, int(causeCodes["Merge situation"]), 
                       int(subCauseCodes["Wants to merge"])])