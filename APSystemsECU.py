#!/usr/bin/env python3

import asyncio
import socket
import binascii
import datetime
import json
import logging

_LOGGER = logging.getLogger(__name__)

from pprint import pprint

class APSystemsInvalidData(Exception):
    pass

class APSystemsInvalidInverter(Exception):
    pass


class APSystemsECU:

    def __init__(self, ipaddr, port=8899, raw_ecu=None, raw_inverter=None):
        self.ipaddr = ipaddr
        self.port = port

        # what do we expect socket data to end in
        self.recv_suffix = b'END\n'

        # how long to wait on socket commands until we get our recv_suffix
        self.timeout = 5

        # how many times do we try the same command in a single update before failing
        self.cmd_attempts = 3

        # how big of a buffer to read at a time from the socket
        self.recv_size = 1024

        # how long to wait between socket open/closes
        self.socket_sleep_time = 2.0
        self.cmd_suffix = "END\n"
        self.ecu_query = "APS1100160001" + self.cmd_suffix
        self.inverter_query_prefix = "APS1100280002"
        self.inverter_query_suffix = self.cmd_suffix

        self.inverter_signal_prefix = "APS1100280030"
        self.inverter_signal_suffix = self.cmd_suffix

        self.inverter_byte_start = 26

        self.ecu_id = None
        self.ecu_firmware = None
        self.qty_of_inverters = 0
        self.qty_of_online_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.inverters = {}
        self.firmware = None
        self.timezone = None
        self.last_update = None
        self.vsl = 0
        self.tsl = 0

        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter
        self.inverter_raw_signal = None

        self.read_buffer = b''

        self.reader = None
        self.writer = None

        self.socket_open = False

        self.errors = []

    async def async_read_from_socket(self):
        self.read_buffer = b''
        end_data = None

        self.read_buffer = await self.reader.readline()
        if self.read_buffer == b'':
            error = f"Got empty string from socket"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        size = len(self.read_buffer)
        end_data = self.read_buffer[size-4:]
        if end_data != self.recv_suffix:
            error = f"End suffix ({self.recv_suffix}) missing from ECU response end_data={end_data} data={self.read_buffer}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        return self.read_buffer

    async def async_send_read_from_socket(self, cmd):
        self.writer.write(cmd.encode('utf-8'))
        await self.writer.drain()
        try:
            return await asyncio.wait_for(self.async_read_from_socket(), timeout=self.timeout)
        except asyncio.TimeoutError as err:
            await self.async_close_socket()
            msg = "Timeout after {self.timeout}s waiting or ECU data cmd={cmd.rstrip()}. Closing socket."
            self.add_error(msg)
            raise APSystemsInvalidData(error)

    async def async_close_socket(self):
        if self.socket_open:
            self.writer.close()
            await self.writer.wait_closed()
            self.socket_open = False

    async def async_open_socket(self):
        _LOGGER.debug(f"Connecting to ECU on {self.ipaddr} {self.port}")
        self.reader, self.writer = await asyncio.open_connection(self.ipaddr, self.port)
        _LOGGER.debug(f"Connected to ECU {self.ipaddr} {self.port}")
        self.socket_open = True


    async def async_query_ecu(self):
        await self.async_open_socket()
        cmd = self.ecu_query
        self.ecu_raw_data = await self.async_send_read_from_socket(cmd)
        await self.async_close_socket()
        self.process_ecu_data()
        if self.lifetime_energy == 0:
            await self.async_close_socket()
            error = f"ECU returned 0 for lifetime energy, raw data={self.ecu_raw_data}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        # the ECU likes the socket to be closed and re-opened between commands
        await asyncio.sleep(self.socket_sleep_time) 
        await self.async_open_socket()
        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        self.inverter_raw_data = await self.async_send_read_from_socket(cmd)
        await self.async_close_socket()

        # the ECU likes the socket to be closed and re-opened between commands
        await asyncio.sleep(self.socket_sleep_time)  
        await self.async_open_socket()
        cmd = self.inverter_signal_prefix + self.ecu_id + self.inverter_signal_suffix
        self.inverter_raw_signal = await self.async_send_read_from_socket(cmd)

        await self.async_close_socket()
        data = self.process_inverter_data()
        data["ecu_id"] = self.ecu_id
        data["ecu_firmware"] = self.firmware
        data["today_energy"] = self.today_energy
        data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power
        data["qty_of_inverters"] = self.qty_of_inverters
        data["qty_of_online_inverters"] = self.qty_of_online_inverters
        return(data)
 
    def aps_int(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+2)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to int location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)
 
    def aps_short(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+1)]), 8)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to short int location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

    def aps_double(self, codec, start):
        try:
            return int (binascii.b2a_hex(codec[(start):(start+4)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to double location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)
    
    def aps_bool(self, codec, start):
        return bool(binascii.b2a_hex(codec[(start):(start+2)]))
    
    def aps_uid(self, codec, start):
        return str(binascii.b2a_hex(codec[(start):(start+12)]))[2:14]
    
    def aps_str(self, codec, start, amount):
        return str(codec[start:(start+amount)])[2:(amount+2)]
    
    def aps_timestamp(self, codec, start, amount):
        timestr=str(binascii.b2a_hex(codec[start:(start+amount)]))[2:(amount+2)]
        return timestr[0:4]+"-"+timestr[4:6]+"-"+timestr[6:8]+" "+timestr[8:10]+":"+timestr[10:12]+":"+timestr[12:14]

    def check_ecu_checksum(self, data, cmd):
        datalen = len(data) - 1
        try:
            checksum = int(data[5:9])
        except ValueError as err:
            debugdata = binascii.b2a_hex(data)
            error = f"Error getting checksum int from '{cmd}' data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        if datalen != checksum:
            debugdata = binascii.b2a_hex(data)
            error = f"Checksum on '{cmd}' failed checksum={checksum} datalen={datalen} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        start_str = self.aps_str(data, 0, 3)
        end_str = self.aps_str(data, len(data) - 4, 3)

        if start_str != 'APS':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect start signature '{start_str}' != APS data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        if end_str != 'END':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect end signature '{end_str}' != END data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        return True

    def process_ecu_data(self, data=None):
        if not data:
            data = self.ecu_raw_data

        self.check_ecu_checksum(data, "ECU Query")
        self.ecu_id = self.aps_str(data, 13, 12)
        self.lifetime_energy = self.aps_double(data, 27) / 10
        self.current_power = self.aps_double(data, 31)
        self.today_energy = self.aps_double(data, 35) / 100
        if self.aps_str(data,25,2) == "01":
            self.qty_of_inverters = self.aps_int(data, 46)
            self.qty_of_online_inverters = self.aps_int(data, 48)
            self.vsl = int(self.aps_str(data, 52, 3))
            self.firmware = self.aps_str(data, 55, self.vsl)
            self.tsl = int(self.aps_str(data, 55 + self.vsl, 3))
            self.timezone = self.aps_str(data, 58 + self.vsl, self.tsl)
        elif self.aps_str(data,25,2) == "02":
            self.qty_of_inverters = self.aps_int(data, 39)
            self.qty_of_online_inverters = self.aps_int(data, 41)
            self.vsl = int(self.aps_str(data, 49, 3))
            self.firmware = self.aps_str(data, 52, self.vsl)

    def process_signal_data(self, data=None):
        signal_data = {}
        if self.inverter_raw_signal != '' and (self.aps_str(self.inverter_raw_signal,9,4)) == '0030':
            data = self.inverter_raw_signal
            _LOGGER.debug(binascii.b2a_hex(data))
            self.check_ecu_checksum(data, "Signal Query")
            if not self.qty_of_inverters:
                return signal_data
            location = 15
            for i in range(0, self.qty_of_inverters):
                uid = self.aps_uid(data, location)
                location += 6
                strength = data[location]
                location += 1
                strength = int((strength / 255) * 100)
                signal_data[uid] = strength
            return signal_data

    def process_inverter_data(self, data=None):
        if not data:
            data = self.inverter_raw_data

        self.check_ecu_checksum(data, "Inverter data")

        output = {}

        timestamp = self.aps_timestamp(data, 19, 14)
        inverter_qty = self.aps_int(data, 17)

        self.last_update = timestamp
        output["timestamp"] = timestamp
        output["inverter_qty"] = inverter_qty
        output["inverters"] = {}

        # this is the start of the loop of inverters
        istr = ''
        cnt2 = self.inverter_byte_start
        signal = self.process_signal_data()
        inverters = {}
        
        for i in range(0, inverter_qty):
            inv={}
            inverter_uid = self.aps_uid(data, cnt2)
            inv["uid"] = inverter_uid
            inv["online"] = bool(self.aps_short(data, cnt2 + 6))
            istr = self.aps_str(data, cnt2 + 7, 2)
            inv["signal"] = signal.get(inverter_uid, 0)
            inv["frequency"] = self.aps_int(data, cnt2 + 9) / 10
            inv["temperature"] = self.aps_int(data, cnt2 + 11) - 100
            if istr == '01' or istr == '04':
                (channel_data, cnt2) = self.process_yc600_ds3(data, cnt2)
                inv.update(channel_data)    
            elif istr == '02':
                (channel_data, cnt2) = self.process_yc1000(data, cnt2)
                inv.update(channel_data)
            elif istr == '03':
                (channel_data, cnt2) = self.process_qs1(data, cnt2)
                inv.update(channel_data)
            else:
                error = f"Unsupported inverter type {inverter_type} please create GitHub issue."
                self.add_error(error)
                raise APSystemsInvalidData(error)
            inverters[inverter_uid] = inv
        self.inverters = inverters
        output["inverters"] = inverters
        return (output)
    
    def process_yc1000(self, data, cnt2):
        power = []
        voltages = []
        power.append(self.aps_int(data, cnt2 + 13))
        voltages.append(self.aps_int(data, cnt2 + 15))
        power.append(self.aps_int(data, cnt2 + 17))
        voltages.append(self.aps_int(data, cnt2 + 19))
        power.append(self.aps_int(data, cnt2 + 21))
        voltages.append(self.aps_int(data, cnt2 + 23))
        power.append(self.aps_int(data, cnt2 + 25))
        output = {
            "model" : "YC1000",
            "channel_qty" : 4,
            "power" : power,
            "voltage" : voltages
        }
        return (output, cnt2)

    def process_qs1(self, data, cnt2):
        power = []
        voltages = []
        power.append(self.aps_int(data, cnt2 + 13))
        voltages.append(self.aps_int(data, cnt2 + 15))
        power.append(self.aps_int(data, cnt2 + 17))
        power.append(self.aps_int(data, cnt2 + 19))
        power.append(self.aps_int(data, cnt2 + 21))
        output = {
            "model" : "QS1",
            "channel_qty" : 4,
            "power" : power,
            "voltage" : voltages
        }
        return (output, cnt2)

    def process_yc600_ds3(self, data, cnt2):
        power = []
        voltages = []
        power.append(self.aps_int(data, cnt2 + 13))
        voltages.append(self.aps_int(data, cnt2 + 15))
        power.append(self.aps_int(data, cnt2 + 17))
        voltages.append(self.aps_int(data, cnt2 + 19))
        output = {
            "model" : "YC60/DS3-D-L",
            "channel_qty" : 2,
            "power" : power,
            "voltage" : voltages,
        }
        return (output, cnt2)

    def add_error(self, error):
        timestamp = datetime.datetime.now()

        self.errors.append("[{timestamp}] {error}")
