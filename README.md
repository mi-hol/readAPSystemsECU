# readAPSystemsECU
read inverter values from APSystems ECUs on any computer having a python3 installation.

- Limitations:
  - ECU queries Inverter only once every 5 minutes! This can't be changed!
  - more detailed data points known to inverter (i.e. DC voltage and current per panel) are not provided  

- Tested with:

  - Hardware:
    - APSystems ECU-B firmware:1.2.34 and DS3 Serial: 7020#####
  
  - Software:
    - Python 3.12.8 on Windows 11 with PowerShell 7.4.x

- Required configuration before running script:

  - adapt parameters between #////////// START USER CONFIGURATION \\\\\\\\\\ and #\\\\\\\\\\ END USER CONFIGURATION ////////// to match your setup

- How to execute:

```
PS C:\Users\U1> ."C:\Users\U1\Documents\readAPSystemsECU\ECU_B.py"
Inverter data timestamp : 2024-12-14 13:45:28
Current total power (DC): 80 W  
Today energy : 0.92 kWh
...
```
