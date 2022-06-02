# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

import paho.mqtt.client as mqttClient
import string, threading
from script.msg.cam import *
from script.msg.cpm import *
from script.msg.denm import *
from script.test.test_laneMerge import subscribe

# The class taht represents the OBUs
class OBU(threading.Thread):
    ip: string
    id: int
    stationType : int
    client: mqttClient

    # The OBU constructor
    def __init__(self, ip: string, id: int):
        super(OBU, self).__init__()
        self.ip = ip
        self.id = id
        self.stationType = 5                    # OBUs are all station type = 5
        self.client = self.connect_mqtt()
        
    # Method to connect to MQTT
    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("OBU_"+str(self.id)+": is connected to MQTT Broker!")
            else:
                print("OBU_"+str(self.id)+": failed to connect, return code %d\n", rc)

        client = mqttClient.Client("OBU_"+str(self.id))
        client.on_connect = on_connect
        client.connect(self.ip)
        return client

    # Method to publish the CAM messages
    # TODO Future Work: the fields "acceleration", "brakePedal" and "gasPedal" could be variables
    # TODO -> i put the altitude at 8m because it's Aveiro's altitude value
    # data -> list with the variables data 
    # data[0]: latitude;
    # data[1]: longitude;
    # data[2]: speed;
    def publish_CAM(self, data: list):
        msg = CAM(True, 0, 8, 15, True, True, True, 1023, "FORWARD", True, False, 3601, 127, data[0], 100,
                  data[1], 4095, 3601, 4095, SpecialVehicle(PublicTransportContainer(False)), data[2],
                  127, True, self.id, self.stationType, 30, 0)

        result = self.client.publish("vanetza/in/cam", repr(msg))
        status = result[0]

        if status == 0:
            print("OBU_"+str(self.id)+": sent CAM msg to topic vanetza/in/cam")
        else:
            print("OBU_"+str(self.id)+": failed to send CAM message to topic vanetza/in/cam")

    # Method to publish the DENM messages
    # TODO Future Work: the field "originatingStationID" -> the id of the DENM sender to coorelate 
    #      with the "stationID" field of the CAM messages 
    # TODO -> what about the "detectionTime" and "referenceTime" fields?
    # TODO -> i put the altitude at 8m because it's Aveiro's altitude value
    # data -> list with the variables data 
    # data[0]: latitude;
    # data[1]: longitude;
    # data[2]: causeCode;
    # data[3]: subCauseCode;
    def publish_DENM(self, data: list):
        msg = DENM(Management(ActionID(self.id, 0), 1626453837.658, 1626453837.658,
                   EventPosition(data[0], data[1], PositionConfidenceEllipse_DENM(0, 0, 0), 
                   Altitude_DENM(8, 1)), 0, 0), Situation(7, EventType(data[2], data[3])))

        result = self.client.publish("vanetza/in/denm", repr(msg))
        status = result[0]

        if status == 0:
            print("OBU_"+str(self.id)+": sent DENM msg to topic vanetza/in/denm")
        else:
            print("OBU_"+str(self.id)+": failed to send DENM message to topic vanetza/in/denm")

    # Method to publish the CPM messages
    # TODO ALL THIS CLASS IS FUTURE WORK !!!!!!!!!!!!!!!!!!!!
    # TODO check this variables fields -> which ones are variable which are not
    # TODO -> i put the altitude at 8m because it's Aveiro's altitude value
    # data -> list with the variable information
    # data[0]: latitude;
    # data[1]: longitude;
    # data[2]: speed; TODO -> is the speed of the OBU or the speed of others OBU detected?
    # def publish_CPM(self, data: list):
    #     # TODO -> what are this sensors?
    #     sensors = [SensorInformationContainer(1, 1, DetectionArea(StationarySensorRectangle(750, 20, 3601))), 
    #                SensorInformationContainer(2, 12, DetectionArea(None, StationarySensorRadial(100, 3601, 3601)))]

    #     # TODO -> what we do with this objects
    #     objects = [PerceivedObjectContainer(1, 0, 0, Axis(1216.281028098143, 1), 
    #                Axis(1216.281028098143, 1), Axis(11.273405440822678, 1), 
    #                Axis(7.9592920392978215, 1), XAcceleration(-0.0011505823066771444, 0),
    #                YAcceleration(-0.000812338440426394, 0), 0, [Classification(0, Class(Vehicle(3, 0)))]), 
                
    #                PerceivedObjectContainer(4, 0, 0, Axis(1216.281028098143, 1),
    #                Axis(1216.281028098143, 1), Axis(-0.5581092564671636, 1),
    #                Axis(-0.7060552795962012, 1), XAcceleration(-0.0, 0),
    #                YAcceleration(-0.0, 0), 0, [Classification(0, Class(None, Other(0, 0)))])]

    #     msg = CPM(44258, CpmParameters(ManagementContainer(self.stationType, 
    #               ReferencePosition(data[0], data[1], 
    #               PositionConfidenceEllipse_CPM(4095, 4095, 0.0), Altitude_CPM(8, 14))), 
    #               StationDataContainer(OriginatingVehicleContainer(Heading(3601, 127), 
    #               Speed(data[2], 127), 0,)), list(sensors), list(objects), len(objects)))

    #     result = self.client.publish("vanetza/in/cpm", repr(msg))
    #     status = result[0]

    #     if status == 0:
    #         print("OBU_"+str(self.id)+": sent CPM msg to topic vanetza/in/cpm")
    #     else:
    #         print("OBU_"+str(self.id)+": failed to send CPM message to topic vanetza/in/cpm")


    # Subscribes the CAM and DENM topic -> it receives an client of the mqttClient type
    def subscribe(self):
        def on_message(client, userdata, msg):
            print("OBU_"+str(self.id)+": received "+msg.payload.decode())

        self.client.subscribe([("vanetza/out/cam", 0), ("vanetza/out/denm", 1)])
        self.client.on_message = on_message
        self.client.loop_forever()

    # To always mantain the subscribe method runing on the background
    def run(self):  
        self.subscribe()