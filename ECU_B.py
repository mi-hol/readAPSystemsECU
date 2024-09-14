#!/usr/bin/env python3

# original source: https://github.com/Doudou14/Domoticz-apsystems_ecu/blob/main/ECU/ECU_B.py
# important findings of reverse engineering of APSystems ECU are in https://community.home-assistant.io/t/apsystems-aps-ecu-r-local-inverters-data-pull/260835/238
 
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
ConsumptionPannel1 = 0  #Inverter 1
ConsumptionPannel2 = 0  #Inverter 1
ConsumptionPannel3 = 0  #Inverter 1 or 2
ConsumptionPannel4 = 0  #Inverter 1 or 2
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

puntcomma = '\u003B'
loop = asyncio.get_event_loop()
ecu = APSystemsECU(ecu_ip)

data = loop.run_until_complete(ecu.async_query_ecu())

#to debug data sent via JSON uncomment pprint
#pprint(data)

#lifetime_energy = str(data.get('lifetime_energy')*1000)
lifetime_energy = str(data.get('lifetime_energy'))
#today_energy = str(data.get('today_energy')*1000)
today_energy = str(data.get('today_energy'))
print('Today energy : ' + today_energy + ' kWh')
current_power = str(data.get('current_power'))
# Todo: correct AC power extraction
print('Current power (AC): ' + current_power + ' W')
#generated_energy = (current_power + puntcomma + lifetime_energy)
print('Total energy : ' + lifetime_energy + ' kWh')

""" 
   if (float(today_energy) >= 0 or float(current_power) >= 0):
   getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': SolarGeneration, 'svalue': (generated_energy)}
   webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
   print(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': Timestamp, 'svalue': data.get('timestamp') + ' / ' + data.get('ecu_firmware')}
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
   nPower = len(data['inverters'][Inverter]['power'])
   nVoltage = len(data['inverters'][Inverter]['voltage'])
   voltage = data['inverters'][Inverter]['voltage'][0]
   # ToDo: correct DC voltage extraction
   # add DC current
   print('Voltage inverter (DC) ' + str(i + 1) + ' panel ' + str(1) + ': ' + str(voltage) + ' V')
   for x in range(nPower):
      power = data['inverters'][Inverter]['power'][x]
      print('Power inverter (DC)' + str(i + 1) + ' panel ' + str(x + 1) + ': ' + str(power) + ' W')

"""
      #upload values to Domoticz for inverter 1
      if (i == 0) and (x == 0) :
         if (float(InverterTemperature) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': TemperatureInverter1, 'svalue': InverterTemperature}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(InverterFrequency) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': FrequencyInverter1, 'svalue': InverterFrequency}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': SignalInverter1, 'svalue': InverterSignal}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(voltage) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': VoltageInverter1, 'svalue': (voltage)}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
         if InverterOnline == True :
            getVars = {'type' : 'command', 'param' : 'switchlight', 'idx': SwitchInverter1, 'switchcmd': 'On'}
         else :
            getVars = {'type' : 'command', 'param' : 'switchlight', 'idx': SwitchInverter1, 'switchcmd': 'Off'}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel1, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
      elif (i == 0) and (x == 1) :
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel2, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
      elif (i == 0) and (x == 2) :
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel3, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
      elif (i == 0) and (x == 3) :
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel4, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')

     #upload values to Domoticz for inverter 2
      if (i == 1) and (x == 0) :
         if (float(InverterTemperature) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': TemperatureInverter2, 'svalue': InverterTemperature}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(InverterFrequency) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': FrequencyInverter2, 'svalue': InverterFrequency}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': SignalInverter2, 'svalue': InverterSignal}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         if (float(voltage) > 0):
            getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': VoltageInverter2, 'svalue': (voltage)}
            webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
         if InverterOnline == True :
            getVars = {'type' : 'command', 'param' : 'switchlight', 'idx': SwitchInverter2, 'switchcmd': 'On'}
         else :
            getVars = {'type' : 'command', 'param' : 'switchlight', 'idx': SwitchInverter2, 'switchcmd': 'Off'}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars))
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel3, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
      elif (i == 1) and (x == 1) :
         getVars = {'type' : 'command', 'param' : 'udevice', 'nvalue' : 0, 'idx': ConsumptionPannel4, 'svalue': (power)}
         webUrl = urllib.request.urlopen(url + urllib.parse.urlencode(getVars) + (puntcomma) + '0')
 """