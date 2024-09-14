#!/usr/bin/env python3

# original source: https://github.com/Doudou14/Domoticz-apsystems_ecu/blob/main/ECU/ECU_B.py
# important findings reverse engineering APSystems ECU communication are in https://community.home-assistant.io/t/apsystems-aps-ecu-r-local-inverters-data-pull/260835/238
 
from APSystemsECU import APSystemsECU
import time
import asyncio
import urllib.request
import urllib.parse
import urllib
from pprint import pprint
 
#////////// START USER CONFIGURATION \\\\\\\\\\

#Change your ECU IP
ecu_ip = "192.168.0.248"

#Change your Domoticz IP
#url = 'http://IP-Domoticz:8080/json.htm?'

#Change your idx
Timestamp = 0
SolarGeneration = 0
SwitchInverter1 = 0
SwitchInverter2 = 0
ConsumptionPanel1 = 0  #Inverter 1
ConsumptionPanel2 = 0  #Inverter 1
ConsumptionPanel3 = 0  #Inverter 1 or 2
ConsumptionPanel4 = 0  #Inverter 1 or 2
TemperatureInverter1 = 0
TemperatureInverter2 = 0
SignalInverter1 = 0
SignalInverter2 = 0
VoltageInverter1 = 0
VoltageInverter2 = 0
FrequencyInverter1 = 0
FrequencyInverter2 = 0

#\\\\\\\\\\ END USER CONFIGURATION //////////

#Communication delay to ECU (sec)

semicolon = '\u003B'
loop = asyncio.get_event_loop()
ecu = APSystemsECU(ecu_ip)

data = loop.run_until_complete(ecu.async_query_ecu())

#to debug data sent via JSON uncomment pprint
pprint(data)

#lifetime_energy = str(data.get('lifetime_energy')*1000)
lifetime_energy = str(data.get('lifetime_energy'))
#today_energy = str(data.get('today_energy')*1000)
today_energy = str(data.get('today_energy'))
print('Today energy : ' + today_energy + ' kWh')
current_power = str(data.get('current_power'))
# Todo: correct AC power extraction
print('Current total power (DC): ' + current_power + ' W')
#generated_energy = (current_power + semicolon + lifetime_energy)
print('Total energy : ' + lifetime_energy + ' kWh')

""" 
   if (float(today_energy) >= 0 or float(current_power) >= 0):
   getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': SolarGeneration, 'str_value': (generated_energy)}
   webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
   print(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': Timestamp, 'str_value': data.get('timestamp') + ' / ' + data.get('ecu_firmware')}
webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
print(url + urllib.parse.urlencode(getVars))
 """

#inverter values
inverters = data.get('inverters')
#count number of inverters
Inverter_qty = len(data.get('inverters'))
print('Number inverter: ' + str(Inverter_qty))
# loop trough all inverters and get the data
for i in range(Inverter_qty):
   Inverter = list(inverters.keys())[i]
   print('Inverter Id: ' + Inverter)
   InverterFrequency = data['inverters'][Inverter]['frequency']
   print('Frequency: ' + str(InverterFrequency) + ' Hz')
   InverterSignal = data['inverters'][Inverter]['signal']
   print('Signal: ' + str(InverterSignal) + ' %')
   InverterTemperature = data['inverters'][Inverter]['temperature']
   print('Temperature: ' + str(InverterTemperature) + ' °C')
   nPower = len(data['inverters'][Inverter]['DC_power'])
   nVoltage = len(data['inverters'][Inverter]['DC_voltage'])
   voltage = data['inverters'][Inverter]['DC_voltage'][0]
   # ToDo: correct DC voltage extraction for inverter
   # add DC current
   print('Inverter voltage (AC): ' + str(voltage) + ' V')
   for x in range(nPower):
      power = data['inverters'][Inverter]['DC_power'][x]
      print('Power (DC) panel ' + str(x + 1) + ': ' + str(power) + ' W')

"""
      #upload values to Domoticz for inverter 1
      if (i == 0) and (x == 0) :
         if (float(InverterTemperature) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': TemperatureInverter1, 'str_value': InverterTemperature}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(InverterFrequency) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': FrequencyInverter1, 'str_value': InverterFrequency}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': SignalInverter1, 'str_value': InverterSignal}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(voltage) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': VoltageInverter1, 'str_value': (voltage)}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
         if InverterOnline == True :
            getVars = {'type' : 'command', 'param' : 'switch_light', 'idx': SwitchInverter1, 'switch_cmd': 'On'}
         else :
            getVars = {'type' : 'command', 'param' : 'switch_light', 'idx': SwitchInverter1, 'switch_cmd': 'Off'}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel1, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
      elif (i == 0) and (x == 1) :
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel2, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
      elif (i == 0) and (x == 2) :
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel3, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
      elif (i == 0) and (x == 3) :
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel4, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')

     #upload values to Domoticz for inverter 2
      if (i == 1) and (x == 0) :
         if (float(InverterTemperature) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': TemperatureInverter2, 'str_value': InverterTemperature}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(InverterFrequency) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': FrequencyInverter2, 'str_value': InverterFrequency}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': SignalInverter2, 'str_value': InverterSignal}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(voltage) > 0):
            getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': VoltageInverter2, 'str_value': (voltage)}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
         if InverterOnline == True :
            getVars = {'type' : 'command', 'param' : 'switch_light', 'idx': SwitchInverter2, 'switch_cmd': 'On'}
         else :
            getVars = {'type' : 'command', 'param' : 'switch_light', 'idx': SwitchInverter2, 'switch_cmd': 'Off'}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel3, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
      elif (i == 1) and (x == 1) :
         getVars = {'type' : 'command', 'param' : 'user_device', 'num_value' : 0, 'idx': ConsumptionPanel4, 'str_value': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (semicolon) + '0')
 """