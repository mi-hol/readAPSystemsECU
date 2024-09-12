#!/usr/bin/env python3

# source: ??  
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

        self.ecu_id = self.aps_str(data, 13, 12)
        self.qty_of_inverters = self.aps_int(data, 46)
        self.firmware = self.aps_str(data, 55, 15)
        self.timezone = self.aps_str(data, 70, 9)

    def process_inverter_data(self, data=None):
        if not data:
            data = self.inverter_raw_data

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
                (channel_data, location) = self.process_yc600(data, location)
                inv.update(channel_data)    

            # a QS1 starts with 8020
            elif inverter_uid.startswith("8020"):
                (channel_data, location) = self.process_qs1(data, location)
                inv.update(channel_data)    

            # a DS3S starts with 7020
            elif inverter_uid.startswith("7020"):
                (channel_data, location) = self.process_ds3(data, location)
                inv.update(channel_data)    

            # a DS3M starts with 7070
            elif inverter_uid.startswith("7070"):
                (channel_data, location) = self.process_ds3(data, location)
                inv.update(channel_data)    

            inverters.append(inv)

        total_power = 0
        for i in inverters:
            # ToDo: fix index ["power"]  triggers error below , if label is renamed!!
            for p in i["power"]:
                total_power += p


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
            "power" : power,
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
            "power" : power,
            "voltage" : voltages,
        }

        return (output, location)

    def process_ds3(self, data, location):
        power = []
        voltages = []
        dc_i = []
        dc_p = []

        for i in range(0, 2):
            power.append(self.aps_int(data, location))
            location += 2

            voltages.append(self.aps_int(data, location))
            location += 2

        output = {
            "model" : "DS3",
            "channel_qty" : 2,
            "power" : power,
            # "AC power" : power,
            # triggers error in line 164, in process_inverter_data 
            # for p in i["power"]:
            # ~^^^^^^^^^
            #    KeyError: 'power'
            "AC voltage" : voltages
        }

        return (output, location)


if __name__ == "__main__":

    # supply the correct IP address here
    ecu = APSystemsECU("192.168.0.248")

    # get inverter data by querying the ecu directly
    ecu.query_ecu()
    print(ecu.dump())
    print("*** End ECU data ***")
    
    data = ecu.query_inverters()
    print(json.dumps(data, indent=2))


    # sample_yc600_data = bytes.fromhex('415053313130313736303030323030303100072020112412051040800009401601303101f3006f001400e4001400e440800009562201303101f3006f001300e4001400e440800009182601303101f3006f001400e3001400e340800009293301303101f3006f001400e3001300e340800009191301303101f3006f001500e3001400e340800009243401303101f3006f001400e3001400e340800009184001303101f3006f001400e2001400e2454e440a')
    # data = ecu.process_inverter_data(data = sample_yc600_data)
    # print(json.dumps(data, indent=2))

    # sample_qs1_data = bytes.fromhex('415053313130313930303030323030303100072020122915125380200010441301303302570065000200f100010007000680200011026901303302570064000100f200010006000680200011054901303302570065000100f100010006000680200011131401303302570064000100f100000006000680200011234201303302570065000000ef00010005000680200011330401303302570065000400f000000000000080200011352301303302570066000100f1000100060006454e440a')
    # data = ecu.process_inverter_data(data = sample_qs1_data)
    # print(json.dumps(data, indent=2))
	
	