# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

import paho.mqtt.client as mqttClient
import string, threading, json, geopy
from script.msg.cam import *
from script.msg.cpm import *
from script.msg.denm import *
from time import sleep

# Speed values
speed_values = [60, 80, 100, 120, 140]

# Delta distance - the default move distance that a OBU mades 
delta_dist = 5

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
                  data[2], 127, True, self.id, self.stationType, 30, 0)

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
        # if status == 0:
        #     print("OBU_"+str(self.id)+": sent DENM msg to topic vanetza/in/denm")
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
            self.denm_queue.append(data)
        # If it's a CAM msg
        else:
            data = { "stationID": msg["stationID"],
                     "latitude": msg["latitude"],
                     "longitude": msg["longitude"],
                     "speed": msg["speed"]
                   }
            print("OBU_"+str(self.id)+" received CAM: "+str(data))
            self.cam_queue.append(data)
            
    # To pop the first item of the CAM msgs queue
    def popItemInCamQueue(self):
        self.cam_queue.pop(0)
    
    # To pop the first item of the DENM msgs queue
    def popItemInDenmQueue(self):
        self.denm_queue.pop(0)

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
            # If it's the OBU that starts runing on the merge lane of the highway
            if(self.id == 1):
                if (i < 7):
                    pos = geopy.distance.geodesic(meters = delta_dist*i).destination(start, 222)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
                else:
                    pos = geopy.distance.geodesic(meters = delta_dist*i).destination(start, 223)
                    # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
            # If the OBU starts on the main lane of the highway
            else:
                pos = geopy.distance.geodesic(meters = delta_dist*i).destination(start, 225)
                # print("["+str(pos.latitude)+", "+str(pos.longitude)+"],")
            
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
        print("OBU_"+str(self.id)+" is on: "+str(self.actual_pos))

    # Developer-friendly string representation of the object
    def obu_status(self):
        repr = {"actual_pos": self.actual_pos,
                "speed": self.speed}
        return repr

    # To truncate an number with the number of decimals passed as argument
    def truncate(self, num, dec_plc):
        return int(num * 10**dec_plc) / 10**dec_plc