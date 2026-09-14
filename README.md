
# Kikusui_Power_Supply_battery_charge
Kikusui Power Supply LION battery charge program

## Overview
Kikusui Power Supply LION battery charge program is written in Python. <p>
#### Features
  1. Kikusui power supplies are controlled in CC and CV (constant voltage) mode.
  2. The current ramps at 0.01A/step (default step = 1 seconds).
  3. Plots the power supply's voltage and current in real time.
  4. Manually saves time history data.
#### Usage
  1. Open program: Click KIKUSUI_PMX18-5A_Battery_Charge.py
  2. To start the program, press the following buttons in order:
     - “Enable Remote Mode“ Button
     - “Power Supply Ready“ Button
     - “Manual Mode“ Button with setting traget voltage
     - “Start Button“ to start the program
  4. “Pause//Resume": Pressing the “Pause//Resume” button, voltage status hold or resume.
  5. “Output File": : Push the button to save Time history data　in CSV data file.
  6. To stop program, press the below buttons in order:
     - “Stop“ Button
     - “Power Supply Disable“ Button
     - “Back to Local Mode“ Button
  7. Input:
     - “Time Interval_transient“ to control this module, default is 1 sec/step.(typical)
     - “Time Interval_stable“  If control cmd state is stable(constant), control time interval is 10sec/step.(typical)
     - “Phase1 CC Charge (Voltage)“  Voltage changing from Phase0(Trickle charge) to Phase1(CC Charge).
     - “Phase2 CV Charge (Voltage)“  Voltage changing from Phase1(CC charge) to Phase2(CV Charge).
     - “Phase0 Tricle Charge rate(A)“  Current in Phase0(Trickle charge), default is 10mA.
     - “Phase1 CC Charge rate(A)“  Current in Phase1(CC charge).
     - “Terminate Condition1　Maximum time(min)“ 　The CV charging will stop after a certain amount of time has elapsed since entering Phase 2. Typical is 60 min.
     - “Terminate Condition2　Current(A)“ 　The CV charging will stop when the current drops to this value. Typical is 1/10th of its CC value.

<img width="945" height="890" alt="image" src="https://github.com/user-attachments/assets/fb5c6706-877c-4b6d-865a-9f7caf2b0e5d" />
<p> LION battery charge program <p>

<img width="945" height="890" alt="image" src="https://github.com/user-attachments/assets/705e2071-5cb5-4572-b105-b6bbf2917f28" />
<p> Voltage and Current protection limit change Tab

#### Notes  
  1. It is usable for KIKUSUI solo-Power supply. <p>
  
## Development Environment
#### Hardware Environment
  1. Kikusui Power supply PMX18-5A.(PMX-A series and other Kikusui single Power Supples. Dual power supply is not available.)
  2. Windows PC
#### Software Environment
  1. OS: Windows11
  2. Python: Version 3.11.9
  3. Front end Libraries: pyvisa, numpy, matplotlib
  4. VISA Back end Libraries: National Instrument 「NI-488.2」,「NI-VISA」
  5. USB driver (windows11 default drivers)
#### Known issue


## Related material
  1. [Kikusui Power supply PMX-A Series](https://kikusui.co.jp/w2-2/dc-power-supply/pmx-a/pmx-a/)
  2. [Kikusui Sample Cord for Python](https://kikusui.co.jp/download/python/)
  3. [National Instrument NI-488.2](https://www.ni.com/ja-jp/support/downloads/drivers/download.ni-488-2.html#467646)
  4. [National Instrument NI-VISA](https://www.ni.com/ja-jp/support/downloads/drivers/download.ni-visa.html#346210)

