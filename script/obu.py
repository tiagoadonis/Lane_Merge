# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

from ctypes.wintypes import PINT
import paho.mqtt.client as mqttClient
import string, threading, json, geopy
from script.msg.cam import *
from script.msg.cpm import *
from script.msg.denm import *
from time import sleep

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
    speed: int
    actual_pos: list
    done: bool
    stationType: int
    client: mqttClient
    wants_to_merge: bool
    tot_obus: int
    obus_not_blocking: int
    first_iteraction: bool
    merging: bool

    # The OBU constructor
    def __init__(self, ip: string, id: int, start_pos: list, speed: int):
        super(OBU, self).__init__()
        self.ip = ip
        self.id = id
        self.start_pos = start_pos
        self.speed = speed
        self.done = False
        self.stationType = 5                    # OBUs are all station type = 5
        self.client = self.connect_mqtt()
        self.wants_to_merge = False
        self.tot_obus = 0
        self.obus_not_blocking = 0
        self.first_iteraction = True
        self.merging = False
        
    # Method to connect to MQTT
    def connect_mqtt(self):
        # def on_connect(client, userdata, flags, rc):
        #     if rc == 0:
        #         print("OBU_"+str(self.id)+": is connected to MQTT Broker!")
        #     else:
        #         print("OBU_"+str(self.id)+": failed to connect, return code %d\n", rc)

        client = mqttClient.Client("OBU_"+str(self.id))
        # client.on_connect = on_connect
        client.connect(self.ip)
        return client

    # Method to publish the CAM messages
    # TODO Future Work: the fields "acceleration", "brakePedal" and "gasPedal" could be variables
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
            # print("OBU_"+str(self.id)+": sent CAM msg to topic vanetza/in/cam")
            print("OBU_"+str(self.id)+" CAM: Latitude: "+str(self.truncate(data[0], 7))+
                  ", Longitude: "+str(self.truncate(data[1], 7))+", Speed: "+str(data[2]))
        # else:
        #     print("OBU_"+str(self.id)+": failed to send CAM message to topic vanetza/in/cam")

    # Method to publish the DENM messages
    # TODO Future Work: the field "originatingStationID" -> the id of the DENM sender to coorelate 
    #      with the "stationID" field of the CAM messages 
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
        #   print("OBU_"+str(self.id)+": sent DENM msg to topic vanetza/in/denm")
            print("OBU_"+str(self.id)+" DENM: Latitude: "+str(self.truncate(data[0], 7))+", Longitude: "
                  +str(self.truncate(data[1], 7))+", CauseCode: "+str(data[2])+", SubCauseCode: "+str(data[3]))
        # else:
        #     print("OBU_"+str(self.id)+": failed to send DENM message to topic vanetza/in/denm")

    # Gets an Json object from the mesg received in the subscribe method 
    def getJson(self, msg):
        # If it's a DENM msg
        if("fields" in msg):
            data = { "stationID": msg["stationID"],
                     "latitude": msg["fields"]["denm"]["management"]["eventPosition"]["latitude"],
                     "longitude": msg["fields"]["denm"]["management"]["eventPosition"]["longitude"],
                     "causeCode": msg["fields"]["denm"]["situation"]["eventType"]["causeCode"],
                     "subCauseCode": msg["fields"]["denm"]["situation"]["eventType"]["subCauseCode"],
                   }
            print("OBU_"+str(self.id)+" received DENM: "+str(data))
            self.processEvents(data)

        # If it's a CAM msg
        else:
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

            # Check if it's posible to merge
            if(self.wants_to_merge):
                # print("Tot OBUS: "+str(self.tot_obus))
                self.checkIfNextLaneIsClear(data)
                # The merge is approved, the OBU is going to merge
                if(self.tot_obus == self.obus_not_blocking):
                    print("OBU_"+str(self.id)+" MERGE APPROVED")
                    self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                        causeCodes["Merge situation"], subCauseCodes["Going to merge"]] )

                    # The others OBUs maintain the speed
                    if(data["stationID"] != self.id):
                        unfactor_coords = self.unfactorCoords([data["latitude"], data["longitude"]])
                        self.publish_DENM( [unfactor_coords[0], unfactor_coords[1], 
                                        causeCodes["Mantain speed"], causeCodes["Mantain speed"]] )

                    self.speed = speed_values[2]
                    self.merging = True
                    self.wants_to_merge = False

    # Gets the message received on the subscribes topics
    def get_sub_msg(self, client, userdata, msg):
        # print("OBU_"+str(self.id)+": received "+msg.payload.decode())
        self.getJson(json.loads(msg.payload.decode()))

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
                    if(i == 11):
                        pos = geopy.distance.geodesic(meters = (self.speed-10)*delta_dist*i).destination(start, 221.3)   
                        self.publish_DENM( [pos.latitude, pos.longitude, 
                                    causeCodes["Merge situation"], subCauseCodes["Merge done"]] )                     
                    if(i >= 12 and i < 17):
                        pos = geopy.distance.geodesic(meters = (self.speed-5)*delta_dist*i).destination(start, 221.3)
                        if (i == 13):
                            self.publish_DENM( [pos.latitude, pos.longitude, 
                                    causeCodes["Merge situation"], subCauseCodes["Merge done"]] )      
                    elif(i >= 17 and i <= 19):
                        pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 221.7)

            # If the OBU starts on the main lane of the highway
            else:
                pos = geopy.distance.geodesic(meters = self.speed*delta_dist*i).destination(start, 225)
                # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
            
            # END of case 1
            if(i == 19):
                self.done = True

            # Publish the CAM msg
            self.publish_CAM([pos.latitude, pos.longitude, self.speed])
            self.updatePos([self.truncate(pos.latitude, 7), self.truncate(pos.longitude, 7)])

            i+=1
            # Send the CAMs at a 1Hz frequency
            sleep(1)

        self.client.loop_stop()
        self.client.disconnect()

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

    # Processes the events received by the DENM messages
    def processEvents(self, data):
        unfactor_coords = self.unfactorCoords([data["latitude"], data["longitude"]])

        # If an OBU is approaching the merge point
        if(data["causeCode"] == causeCodes["Approaching Merge"]):
            if( (unfactor_coords[0] == self.actual_pos[0])  and (unfactor_coords[1] == self.actual_pos[1]) ):
                print("OBU_"+str(self.id)+": i'm approaching an merge point")

                # The OBU sends an DENM message with his merge intention
                print("OBU_"+str(self.id)+" wants to merge")
                self.publish_DENM( [self.actual_pos[0], self.actual_pos[1], 
                                    causeCodes["Merge situation"], subCauseCodes["Wants to merge"]] )

                self.wants_to_merge = True
            
        # The OBU receives the intention of merge by another OBU
        if((data["causeCode"] == causeCodes["Merge situation"]) and (data["subCauseCode"] == subCauseCodes["Wants to merge"])):
            print("OBU_"+str(self.id)+": knows that the OBU_"+str(data["stationID"])+" wants to merge")

    # Helps the merging OBU to know if the next lane is clear or not
    def checkIfNextLaneIsClear(self, data):
        # Calculate only if it's a OBU
        if(data["speed"] > 0):
            actual_pos_point = geopy.Point(self.actual_pos[0], self.actual_pos[1])
            pos_clear = geopy.distance.geodesic(meters = 4).destination(actual_pos_point, 160)

            truncated_coord = [self.truncate(pos_clear.latitude, 7), self.truncate(pos_clear.longitude, 7)]
            unfact_coord = self.unfactorCoords([data["latitude"], data["longitude"]])   

            # Check if the near position on the highway is clear
            if( (truncated_coord[0] != unfact_coord[0]) and (truncated_coord[1] != unfact_coord[1]) ): 
                self.obus_not_blocking+=1