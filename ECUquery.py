#!/usr/bin/env python3

# source: https://community.home-assistant.io/t/apsystems-aps-ecu-r-local-inverters-data-pull/260835/19  
# likely original source:  https://github.com/Doudou14/Domoticz-apsystems_ecu/blob/main/ECU/APSystemsECU.py

import socket
import binascii
import datetime
import json

from pprint import pprint

class APSystemsECU:

    def __init__(self, ipaddr, port=8899, raw_ecu=None, raw_inverter=None):
        self.ipaddr = ipaddr
        self.port = port

        self.recv_size = 2048

        self.ecu_query = 'APS1100160001END'
        self.inverter_query_prefix = 'APS1100280002'
        self.inverter_query_suffix = 'END'
        self.inverter_byte_start = 26

        self.ecu_id = None
        self.qty_of_inverters = 0
        self.inverters = []
        self.firmware = None
        self.timezone = None

        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter

        self.last_inverter_data = None


    def dump(self):
        print(f"ECU : {self.ecu_id}")
        print(f"Firmware : {self.firmware}")
        print(f"TZ : {self.timezone}")
        print(f"Qty of inverters : {self.qty_of_inverters}")

    def query_ecu(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ipaddr,self.port))

        sock.send(self.ecu_query.encode('utf-8'))
        self.ecu_raw_data = sock.recv(self.recv_size)

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        self.process_ecu_data()

    def query_inverters(self, ecu_id = None):
        if not ecu_id:
            ecu_id = self.ecu_id

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ipaddr,self.port))
        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        sock.send(cmd.encode('utf-8'))

        self.inverter_raw_data = sock.recv(self.recv_size)

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        data = self.process_inverter_data()
        self.last_inverter_data = data

        return(data)
 
    def aps_int(self, codec, start):
        return int(binascii.b2a_hex(codec[(start):(start+2)]),16)
    
    def aps_bool(self, codec, start):
        return bool(binascii.b2a_hex(codec[(start):(start+2)]))
    
    def aps_uid(self, codec, start):
        return str(binascii.b2a_hex(codec[(start):(start+12)]))[2:14]
    
    def aps_str(self, codec, start, amount):
        return str(codec[start:(start+amount)])[2:(amount+2)]
    
    def aps_timestamp(self, codec, start, amount):
        timestr=str(binascii.b2a_hex(codec[start:(start+amount)]))[2:(amount+2)]
        return timestr[0:4]+"-"+timestr[4:6]+"-"+timestr[6:8]+" "+timestr[8:10]+":"+timestr[10:12]+":"+timestr[12:14]

    def process_ecu_data(self, data=None):
        if not data:
            data = self.ecu_raw_data

        if len(data) < 16:
            raise Exception("ECU query didn't return minimum 16 bytes, no inverters active.")

        print(f"ECU data: {data.hex()}")
        self.ecu_id = self.aps_str(data, 13, 12)
        self.qty_of_inverters = self.aps_int(data, 46)
        self.firmware = self.aps_str(data, 55, 15)
        self.timezone = self.aps_str(data, 70, 9)

    def process_inverter_data(self, data=None):
        if not data:
            data = self.inverter_raw_data

        print(f"Inverter data: {data.hex()}")

        output = {}

        timestamp = self.aps_timestamp(data, 19, 14)
        inverter_qty = self.aps_int(data, 17)

        output["timestamp"] = timestamp
        output["inverter_qty"] = inverter_qty
        output["inverters"] = []

        # this is the start of the loop of inverters
        location = self.inverter_byte_start

        inverters = []
        for i in range(0, inverter_qty):

            inv={}

            inverter_uid = self.aps_uid(data, location)
            inv["uid"] = inverter_uid
            location += 6

            inv["online"] = self.aps_bool(data, location)
            location += 1

            inv["unknown"] = self.aps_str(data, location, 2)
            location += 2

            inv["AC frequency"] = self.aps_int(data, location) / 10
            location += 2

            inv["temperature"] = self.aps_int(data, location) - 100
            location += 2

            # a YC600 starts with 4080
            if inverter_uid.startswith("4080"):
                Input_channel_qty = 2
                (channel_data, location) = self.process_yc600(data, location)
                inv.update(channel_data)    

            # a QS1 starts with 8020
            elif inverter_uid.startswith("8020"):
                Input_channel_qty = 4
                (channel_data, location) = self.process_qs1(data, location)
                inv.update(channel_data)    

            # a DS3S starts with 7020
            elif inverter_uid.startswith("7020"):
                Input_channel_qty = 2
                (channel_data, location) = self.process_ds3(data, location)
                inv.update(channel_data)    

            # a DS3M starts with 7070
            elif inverter_uid.startswith("7070"):
                Input_channel_qty = 2
                (channel_data, location) = self.process_ds3(data, location)
                inv.update(channel_data)    

            inverters.append(inv)

        total_power = 0
        for inv in inverters:
            if "power_dc" in inv:
                total_power += sum(inv["power_dc"])

        output["total_power (DC)"] = total_power
        output["inverters"] = inverters
        return (output)

    def process_qs1(self, data, location):

        power = []
        voltages = []

        power.append(self.aps_int(data, location))
        location += 2

        voltage = self.aps_int(data, location)
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        voltages.append(voltage)

        output = {
            "model" : "QS1",
            "channel_qty" : 4,
            "power_DC" : power,
            "voltage" : voltages
        }

        return (output, location)


    def process_yc600(self, data, location):
        power = []
        voltages = []

        for i in range(0, 2):
            power.append(self.aps_int(data, location))
            location += 2

            voltages.append(self.aps_int(data, location))
            location += 2

        output = {
            "model" : "YC600",
            "channel_qty" : 2,
            "power_dc" : power,
            "voltage" : voltages,
        }

        return (output, location)

    def process_ds3(self, data, location):
        power = []
        voltages = []
        dc_i = []
        dc_p = []

        for i in range(0, 2):
            #Appends the  current value from the data at the current location to the corresponding lists.
            #Increments the location by 2 to move to the next data point.

            power.append(self.aps_int(data, location))
            location += 2

            voltages.append(self.aps_int(data, location))
            location += 2

            dc_i.append(self.aps_int(data, location))
            location += 2

            #dc_p.append(self.aps_int(data, location))
            #location += 2

        output = {
            "model" : "DS3",
            "channel_qty" : 2,
            "power_dc" : power,
            "AC voltage" : voltages
        }

        return (output, location)


if __name__ == "__main__":

    # ToDo: enter the correct IP address of ECU below
    ecu = APSystemsECU("192.168.0.248")

    # get inverter data by querying the ecu directly
    ecu.query_ecu()
    print(ecu.dump())
    print("*** End ECU data ***")
    
    data = ecu.query_inverters()
    print(json.dumps(data, indent=2))

    # sample_ecu_data   = bytes.fromhex('41505331313030393430303031323136333030303037303034303100004df3000001a900000136d0d0d0d0d0d0d00001000131303031324543555f425f312e322e33333030394574632f474d542d3880971b02db59000000000000454e440a')
    # expect:
    #   ECU : 216300007004
    #   Firmware : ECU_B_1.2.33009
    #   TZ : Etc/GMT-8
    #   Qty of inverters : 1

    # sample_ds3_data   = bytes.fromhex('415053313130303530303030323030303100012024091312593270200099999901303101f3009700d300f000d600f0454e440a')
    # expect: 
    #   "timestamp": "2024-09-13 12:59:32"
#       "uid": "702000999999",
#       "online": true,
#       "unknown": "01",
#       "AC frequency": 49.9,
#       "temperature": 51,
#       "model": "DS3",
#       "channel_qty": 2,
#       "power_dc": [
#         211,
#         214    # todo: fix wrong 240
#       ],
#       "AC voltage": [
#         240,
#         240 # todo: fix wrong
#       ]
#     }
#   ],
#   "total_power (DC)": 425     # todo: fix wrong 451
# }

# todo add:
#  DC-V_1: 44.4 DC-V_2: 43.3 
#  DC-I_1: 5.8  DC-I_2: 6.0 
#  AC-P: 403


    # sample_yc600_data = bytes.fromhex('415053313130313736303030323030303100072020112412051040800009401601303101f3006f001400e4001400e440800009562201303101f3006f001300e4001400e440800009182601303101f3006f001400e3001400e340800009293301303101f3006f001400e3001300e340800009191301303101f3006f001500e3001400e340800009243401303101f3006f001400e3001400e340800009184001303101f3006f001400e2001400e2454e440a')
    # data = ecu.process_inverter_data(data = sample_yc600_data)
    # print(json.dumps(data, indent=2))

    # sample_qs1_data = bytes.fromhex('415053313130313930303030323030303100072020122915125380200010441301303302570065000200f100010007000680200011026901303302570064000100f200010006000680200011054901303302570065000100f100010006000680200011131401303302570064000100f100000006000680200011234201303302570065000000ef00010005000680200011330401303302570065000400f000000000000080200011352301303302570066000100f1000100060006454e440a')
    # data = ecu.process_inverter_data(data = sample_qs1_data)
    # print(json.dumps(data, indent=2))
	
	