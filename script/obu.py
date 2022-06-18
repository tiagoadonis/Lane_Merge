# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from ctypes.wintypes import PINT
import paho.mqtt.client as mqttClient
import string, threading, json, geopy, random
from script.msg.cam import *
from script.msg.cpm import *
from script.msg.denm import *
from time import sleep
from shapely.geometry import Point, Polygon

# Speed values
speed_values = [60, 80, 100, 120, 140]

# Delta distance - the default move distance that a OBU mades 
delta_dist = 0.05

# DENM "causeCodes" and "subCauseCodes"
causeCodes = {"Approaching Merge": 31, "Merge situation": 32, "Change position": 33, 
              "Reduce the speed": 34, "Increase the speed": 35, "Mantain speed": 36}

# The causeCode "Merge situation" has the following subCauseCodes
subCauseCodes = {"Wants to merge": 41, "Going to merge": 42, "Merge done": 43, "Abort merge": 44}

# The class taht represents the OBUs
class OBU(threading.Thread):
    ip: string
    id: int
    start_pos: list
    initial_speed: int
    speed: int
    actual_pos: list
    done: bool
    stationType: int
    client: mqttClient
    wants_to_merge: bool
    tot_obus: int
    first_iteraction: bool
    merging: bool

    # The OBU constructor
    def __init__(self, ip: string, id: int, start_pos: list, speed: int):
        threading.Thread.__init__(self)
        self.ip = ip
        self.id = id
        self.start_pos = start_pos
        self.initial_speed = speed
        self.speed = speed
        self.done = False
        self.stationType = 5                    # OBUs are all station type = 5
        self.client = self.connect_mqtt()
        self.wants_to_merge = False
        self.tot_obus = 0
        self.first_iteraction = True
        self.merging = False

        self.lane_clear_2 = False
        self.lane_clear_3 = False
        self.lane_clear = False
        self.blocking_obu_id = -1
        self.reducing = False  

    # Method to connect to MQTT
    def connect_mqtt(self):
        client = mqttClient.Client("OBU_"+str(self.id))
        client.connect(self.ip)
        return client

    # Method to publish the CAM messages
    # data -> list with the variables data 
    # data[0]: latitude;
    # data[1]: longitude;
    # data[2]: speed;
    def publish_CAM(self, data: list):
        msg = CAM(True, 0, 8, 15, True, True, True, 1023, "FORWARD", True, False, 3601, 127, self.truncate(data[0], 7), 100,
                  self.truncate(data[1], 7), 4095, 3601, 4095, SpecialVehicle(PublicTransportContainer(False)), 
                  data[2], 127, True, self.id, self.stationType, 4, 0)

        result = self.client.publish("vanetza/in/cam", repr(msg))
        status = result[0]

        # DEBUG ONLY
        if status == 0:
            print("OBU_"+str(self.id)+" CAM: Latitude: "+str(self.truncate(data[0], 7))+
                  ", Longitude: "+str(self.truncate(data[1], 7))+", Speed: "+str(data[2]))

    # Method to publish the DENM messages
    # data -> list with the variables data 
    # data[0]: latitude;
    # data[1]: longitude;
    # data[2]: causeCode;
    # data[3]: subCauseCode;
    def publish_DENM(self, data: list):
        msg = DENM(Management(ActionID(self.id, 0), 1626453837.658, 1626453837.658,
                   EventPosition(self.truncate(data[0], 7), self.truncate(data[1], 7), PositionConfidenceEllipse_DENM(0, 0, 0), 
                   Altitude_DENM(8, 1)), 0, 0), Situation(7, EventType(data[2], data[3])))

        result = self.client.publish("vanetza/in/denm", repr(msg))
        status = result[0]

        # DEBUG ONLY
        if status == 0:
            print("OBU_"+str(self.id)+" DENM: Latitude: "+str(self.truncate(data[0], 7))+", Longitude: "
                  +str(self.truncate(data[1], 7))+", CauseCode: "+str(data[2])+", SubCauseCode: "+str(data[3]))

    # Gets the message received on the subscribes topics
    def get_sub_msg(self, client, userdata, msg):
        # print("OBU_"+str(self.id)+": received "+msg.payload.decode())
        msg_type = msg.topic
        msg = json.loads(msg.payload.decode())

        # If it's a DENM msg
        if(msg_type == "vanetza/out/denm"):
            data = { "stationID": msg["stationID"],
                     "latitude": msg["fields"]["denm"]["management"]["eventPosition"]["latitude"],
                     "longitude": msg["fields"]["denm"]["management"]["eventPosition"]["longitude"],
                     "causeCode": msg["fields"]["denm"]["situation"]["eventType"]["causeCode"],
                     "subCauseCode": msg["fields"]["denm"]["situation"]["eventType"]["subCauseCode"],
                   }
            print("OBU_"+str(self.id)+" received DENM: "+str(data))
            self.processEvents(data)

        # If it's a CAM msg
        elif(msg_type == "vanetza/out/cam"):
            data = { "stationID": msg["stationID"],
                     "latitude": msg["latitude"],
                     "longitude": msg["longitude"],
                     "speed": msg["speed"]
                   }
            print("OBU_"+str(self.id)+" received CAM: "+str(data))

            # To know how many OBUs exist on the highway
            if(self.first_iteraction):
                if(data["speed"] > 0):
                    self.tot_obus+=1

            if(self.id == 1):
                if(data["speed"] > 0):
                    self.checkIfLaneIsClear(data)

    # The routine of the OBU objects - "main" method of this class
    def start(self): 
        # Connect to the MQTT
        self.client = mqttClient.Client("OBU_"+str(self.id))
        self.client.connect(self.ip)

        # Subscribes the CAM and DENM topic
        self.client.on_message = self.get_sub_msg
        self.client.loop_start()
        self.client.subscribe([("vanetza/out/cam", 0), ("vanetza/out/denm", 1)])

        # Create the start postion of the OBU
        start = geopy.Point(self.start_pos[0], self.start_pos[1])

        i = 0
        j = 0
        while not self.done:
            if (i > 0):
                self.first_iteraction = False

            # If it's the OBU that starts runing on the merge lane of the highway
            if(self.id == 1):
                if (i < 7):
                    pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 222)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                else:
                    pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 223)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")

                # Adjust the direction when merging
                if(self.merging):
                    pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 223)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                    if(i == 12):
                        pos = geopy.distance.geodesic(meters = (self.speed)*delta_dist*i).destination(start, 221.3)                
                    if(i >= 13 and i < 17):
                        pos = geopy.distance.geodesic(meters = (self.speed)*delta_dist*i).destination(start, 221.3)
                        if (i == 13):
                            self.publish_DENM( [pos.latitude, pos.longitude, 
                                            causeCodes["Merge situation"], subCauseCodes["Merge done"]] )      
                    elif(i >= 17 and i <= 20):
                        pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 221.7)

            # If the OBU starts on the main lane of the highway
            else:
                if(self.reducing):
                    if(j == 0):
                        print("REDUCING FIRST----------------------------------------------------------------------")
                        pos = geopy.distance.geodesic(meters = (self.speed+15)*delta_dist*i).destination(start, 225)
                    elif(j == 1):
                        print("REDUCING SECOND----------------------------------------------------------------------")
                        pos = geopy.distance.geodesic(meters = (self.speed+10)*delta_dist*i).destination(start, 225)  
                    elif(j == 2):
                        print("REDUCING THIRD----------------------------------------------------------------------")
                        pos = geopy.distance.geodesic(meters = (self.speed+5)*delta_dist*i).destination(start, 225)  
                        self.reducing = False  
                    j+=1
                else:
                    pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 225)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                
            # End of simulation
            if(i == 20):
                self.merging = False
                self.done = True

            # Publish the CAM msg
            self.publish_CAM([pos.latitude, pos.longitude, self.speed])
            self.updatePos([self.truncate(pos.latitude, 7), self.truncate(pos.longitude, 7)])

            i+=1
            # Send the CAMs at a 1Hz frequency
            sleep(1)

        self.client.loop_stop()
        self.client.disconnect()

    # Processes the events received by the DENM messages
    def processEvents(self, data):
        unfactor_coords = self.unfactorCoords([data["latitude"], data["longitude"]])

        # If an OBU is approaching the merge point
        if(data["causeCode"] == causeCodes["Approaching Merge"]):
            # Processing the data from the OBU that is on the merge lane
            if( (unfactor_coords[0] == self.actual_pos[0])  and (unfactor_coords[1] == self.actual_pos[1]) ):
                print("OBU_"+str(self.id)+": i'm approaching an merge point")

                # The OBU sends an DENM message with his merge intention
                print("OBU_"+str(self.id)+" wants to merge")
                self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                    causeCodes["Merge situation"], subCauseCodes["Wants to merge"]] )

                self.wants_to_merge = True   
        
        #  If the OBU wants to merge and receives an DENM message 
        if(self.wants_to_merge == True):
            # If the lane on the right side of the merge OBU is clear
            if(self.lane_clear):
                self.wants_to_merge = False

                print("OBU_"+str(self.id)+" merge approved")
                self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                        causeCodes["Merge situation"], subCauseCodes["Going to merge"]] )
                self.merging = True
                print("OBU_"+str(self.id)+" i'm gonna increase my speed")
                self.increaseSpeed()

            # If the lane on the right side of the merge OBU is blocked
            else:
                # The OBU who's on the way informs that he's gonna mantain his speed -> The merge OBU needs to reduce his speed
                if(data["causeCode"] ==  causeCodes["Mantain speed"]):
                    if(data["stationID"] == self.blocking_obu_id):
                        self.wants_to_merge = False
                    
                        self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                            causeCodes["Reduce the speed"], causeCodes["Reduce the speed"]] )
                        self.reducing = True
                        self.reduceSpeed()
                        print("OBU_"+str(self.id)+" i'm gonna reduce my speed")

                        print("OBU_"+str(self.id)+" merge approved")
                        self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                            causeCodes["Merge situation"], subCauseCodes["Going to merge"]] )
                        self.merging = True

                # The OBU who's on the way informs that he's gonna reduce his speed -> The merge OBU will increase his speed
                if(data["causeCode"] == causeCodes["Reduce the speed"]):
                    if(data["stationID"] == self.blocking_obu_id):
                        self.wants_to_merge = False

                        self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                            causeCodes["Increase the speed"], causeCodes["Increase the speed"]] )
                        self.increaseSpeed()

                        print("OBU_"+str(self.id)+" merge approved")
                        self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                            causeCodes["Merge situation"], subCauseCodes["Going to merge"]] )
                        self.merging = True
        
        # The OBU receives the intention of merge by another OBU
        if((data["causeCode"] == causeCodes["Merge situation"]) and (data["subCauseCode"] == subCauseCodes["Wants to merge"])):
            print("OBU_"+str(self.id)+": knows that the OBU_"+str(data["stationID"])+" wants to merge")

            # Check if this OBU is on the near lane of the merge OBU
            if(self.checkIfImBlocking()):
                print("OBU_"+str(self.id)+" i'm on the way")

                # Creates an random option to do the merge situation 
                # TODO -> change this force situation -> put it random
                # option = random.randint(0, 1)
                option = 1
                print("GOING TO CHOSE OPTION: "+str(option))

                # 0) I'm gonna mantain my speed -> The merge OBU needs to reduce his speed
                if (option == 0):
                    self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                        causeCodes["Mantain speed"], causeCodes["Mantain speed"]] )

                # 1) I'm gonna reduce my speed -> The merge OBU needs to increase his speed
                elif (option == 1):
                    self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                        causeCodes["Reduce the speed"], causeCodes["Reduce the speed"]] )
                    print("OBU_"+str(self.id)+" i'm gonna reduce my speed")
                    self.reducing = True
                    self.reduceSpeed()

            # If this OBU is not on the way of the merge OBU
            else:
                print("OBU_"+str(self.id)+" i'm not in the way")
                self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                    causeCodes["Mantain speed"], causeCodes["Mantain speed"]] )

    # To check if the lane on the right side of the merge OBU is clear
    def checkIfLaneIsClear(self, data):
        # Create Point objects
        unfactor_coords = self.unfactorCoords([data["latitude"], data["longitude"]])
        # print("["+str(data["latitude"])+", "+str(data["longitude"])+"]")
        point = Point(self.truncate(unfactor_coords[0], 7), self.truncate(unfactor_coords[1], 7))

        # Create a square
        coords = [(40.6403890, -8.6633100), (40.6403660, -8.6632630), (40.6401800, -8.6635690), (40.6401600, -8.6635250)]
        poly = Polygon(coords)

        if(self.tot_obus == 1):
            if(data["stationID"] == 2):
                if(poly.contains(point) == False):
                    self.lane_clear_2 = True
                    print("THE LANE IS CLEAR: OBU_"+str(data["stationID"])+" : "+str(unfactor_coords))
                else:
                    self.lane_clear_2 = False
                    self.blocking_obu_id = 2
                    print("ATTENTION: THE LANE IS NOT CLEAR: OBU_"+str(data["stationID"])+"------------------------------------")
            self.lane_clear = self.lane_clear_2
        elif(self.tot_obus == 2):
            if(data["stationID"] == 2):
                if(poly.contains(point) == False):
                    self.lane_clear_2 = True
                    print("THE LANE IS CLEAR: OBU_"+str(data["stationID"])+" : "+str(unfactor_coords))
                else:
                    self.lane_clear_2 = False
                    self.blocking_obu_id = 2
                    print("ATTENTION: THE LANE IS NOT CLEAR: OBU_"+str(data["stationID"])+"------------------------------------")
            elif(data["stationID"] == 3):
                if(poly.contains(point) == False):
                    self.lane_clear_3 = True
                    print("THE LANE IS CLEAR: OBU_"+str(data["stationID"])+" : "+str(unfactor_coords))
                else:
                    self.lane_clear_3 = False
                    self.blocking_obu_id = 3
                    print("ATTENTION: THE LANE IS NOT CLEAR: OBU_"+str(data["stationID"])+"------------------------------------")
            self.lane_clear = self.lane_clear_2 and self.lane_clear_3

    # To check if the OBU is blocking the way of the merge OBU
    def checkIfImBlocking(self):
        # 1st -> 40.6403890, -8.6633100
        # 2nd -> 40.6403660, -8.6632630
        # 3rd -> 40.6401800, -8.6635690
        # 4th -> 40.6401600, -8.6635250

        # Create Point objects
        point = Point(self.actual_pos[0], self.actual_pos[1])

        # Create a square
        coords = [(40.6403890, -8.6633100), (40.6403660, -8.6632630), (40.6401800, -8.6635690), (40.6401600, -8.6635250)]
        poly = Polygon(coords)

        return poly.contains(point)

    # Decreases the OBU speed
    def reduceSpeed(self):
        for i in range(0, len(speed_values)):
            if(speed_values[i] == self.speed):
                index = i
        
        if(index != 0):
            self.speed = speed_values[index - 1]

    # Increases the OBU speed
    def increaseSpeed(self):
        for i in range(0, len(speed_values)):
            if(speed_values[i] == self.speed):
                index = i
        
        if(index != (len(speed_values)-1)):
            self.speed = speed_values[index + 1]

    # To update the actual positions coordinates
    def updatePos(self, actual_pos):
        self.actual_pos = actual_pos
        # print("OBU_"+str(self.id)+" is on: "+str(self.actual_pos))

    # Developer-friendly string representation of the object
    def obu_status(self):
        repr = {"actual_pos": self.actual_pos,
                "speed": self.speed}
        return repr

    # To truncate an number with the number of decimals passed as argument
    def truncate(self, num, dec_plc):
        return int(num * 10**dec_plc) / 10**dec_plc

    # To unfactor the coordinates
    def unfactorCoords(self, coords):
        return [coords[0]/(10**7), coords[1]/(10**7)]

    # To reset to the initial state
    def reset(self):
        self.actual_pos = self.start_pos
        self.speed = self.initial_speed
        self.done = False
        self.client.loop_stop()
        self.client.disconnect()

    # Used to stop the simulation
    def stop(self):
        self.done = True