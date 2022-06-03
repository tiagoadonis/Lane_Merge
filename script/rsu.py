# Authors: Tiago Dias   NMEC: 88896
#          Martim Neves NMEC: 88904

import paho.mqtt.client as mqttClient
import string, threading
from script.msg.cam import *
from script.msg.denm import *

# The class taht represents the RSUs
class RSU(threading.Thread):
    ip: string
    id: int
    stationType : int
    client: mqttClient

    # The RSU constructor
    def __init__(self, ip: string, id: int):
        super(RSU, self).__init__()
        self.ip = ip
        self.id = id
        self.stationType = 15                    # RSUs are all station type = 15
        self.client = self.connect_mqtt()

    # Method to connect to MQTT
    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("RSU_"+str(self.id)+": is connected to MQTT Broker!")
            else:
                print("RSU_"+str(self.id)+": failed to connect, return code %d\n", rc)

        client = mqttClient.Client("RSU_"+str(self.id))
        client.on_connect = on_connect
        client.connect(self.ip)
        return client

    # Method to publish the CAM messages at a 1Hz frequency
    # TODO -> we can use the vanetza CAM periodically messages at 1Hz frequency
    # TODO Future Work: the fields "acceleration", "brakePedal" and "gasPedal" could be variables
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
            print("RSU_"+str(self.id)+": sent CAM msg to topic vanetza/in/cam")
        else:
            print("RSU_"+str(self.id)+": failed to send CAM message to topic vanetza/in/cam")

    # Method to publish the DENM messages
    #
    # TODO Future Work: the field "originatingStationID" -> the id of the DENM sender to coorelate 
    #      with the "stationID" field of the CAM messages 
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
            print("RSU"+str(self.id)+": sent DENM msg to topic vanetza/in/denm")
        else:
            print("RSU_"+str(self.id)+": failed to send DENM message to topic vanetza/in/denm")

    # Subscribes the CAM and DENM topic -> it receives an client of the mqttClient type
    def subscribe(self):
        def on_message(client, userdata, msg):
            print("RSU_"+str(self.id)+": received "+msg.payload.decode())

        self.client.subscribe([("vanetza/out/cam", 0), ("vanetza/out/denm", 1)])
        self.client.on_message = on_message
        self.client.loop_forever()

    # To always mantain the subscribe method runing on the background
    def run(self):
        self.subscribe()