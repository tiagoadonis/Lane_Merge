# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from obu import *
from rsu import *
import threading
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

# ------------------------------------------ Lane Merge Class ---------------------------------------- 
class LaneMerge():
    OBUs: list
    rsu: RSU

    # The Lane Merge constructor
    def __init__(self):
        # Create the OBUs
        obu_1 = OBU(obu_1_ip, 1, obu_1_start, 80)
        obu_2 = OBU(obu_2_ip, 2, obu_2_start, 120)

        # Create the RSU
        self.rsu = RSU(rsu_ip, 3, rsu_coords)
        
        # An OBU list with all the OBUs created
        self.OBUs = []
        self.OBUs.append(obu_1)
        self.OBUs.append(obu_2)

    # The method to run the threads of every OBU and RSU
    def run(self):
        # Create and start the RSU thread
        rsu_thread = threading.Thread(target = self.rsu.start)
        rsu_thread.start()

        # Create and start the OBUs threads
        OBUs_threads = []
        for i in range(0, len(self.OBUs)):
            obu_thread = threading.Thread(target = self.OBUs[i].start)
            OBUs_threads.append(obu_thread)
            obu_thread.start()

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