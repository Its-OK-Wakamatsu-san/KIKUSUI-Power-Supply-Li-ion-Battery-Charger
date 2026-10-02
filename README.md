# KIKUSUI PMX18-5A Web-based CV Control & Battery Charger

This project is the main web-based CV control panel and Battery Charger for the KIKUSUI PMX18-5A power supply.

## Main startup flow (web-based CV Control)

1. Open a terminal in the project folder.
2. File set:
   ```
   batch    "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.bat"
   python   "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   html     "C:\Users\directory\templates\KIKUSUI_PMX18-5A_CNTL_index.html"
   favicon  "C:\Users\directory\CV2.png"
   ```
3. Run:
   ```powershell
   KIKUSUI_PMX18-5A_CNTL_web.bat
   ```
4. Open the browser at:
   ```text
   http://localhost:8001
   ```
5. On the page, press the control buttons in this order:
   - Set the target voltage
   - Remote ON
   - Output ON
   - Monitor the live graph and log
6. To stop, press Output OFF or end the server with Ctrl+C.

## Features
- Web-based monitoring of voltage, current, target voltage, and elapsed time
- Live plotted trend graph
- Operation log panel
- Serial command interface through the VISA module

## Notes
- This is the main operation method for the constant voltage power supply.
- Make sure the KIKUSUI power supply is connected and recognized by the system before starting.

## Development environment
- OS: Windows 11
- Python: 3.11+
- Libraries: pyvisa, http, urllib, websockets
- VISA backend: NI-VISA or compatible driver

## Related resources
- [Kikusui PMX-A Series](https://kikusui.co.jp/w2-2/dc-power-supply/pmx-a/pmx-a/)
- [Kikusui Sample Code for Python](https://kikusui.co.jp/download/python/)
- [NI-VISA](https://www.ni.com/ja-jp/support/downloads/drivers/download.ni-visa.html#346210)

## Battery charger Web UI

The battery charger has a WebSocket-based Web UI version.
<img width="1484" height="1081" alt="image" src="https://github.com/user-attachments/assets/cc502b4c-c32b-414d-8f77-054c0b243dc5" />




1. Open a terminal in the project folder.
2. File set:
   ```
   batch    "C:\Users\directory\KIKUSUI_PMX18-5A_Battery_Charge.bat"
   python   "C:\Users\directory\KIKUSUI_PMX18-5A_Battery_Charge.py"
   html     "C:\Users\directory\templates\KIKUSUI_PMX18-5A_Battery_Charge_index.html"
   favicon  "C:\Users\directory\BC2.png"
   ```
4. Run `KIKUSUI_PMX18-5A_Battery_Charge_web.bat` from this folder.
5. Open `http://localhost:8003` in a browser.
6. Connect the VISA resource, enable Remote and Output, then press Start.

The browser receives measurements, charge phase, logs, and graph history over WebSocket once per second. Pause/Resume excludes the paused time from elapsed charge time. `Stop` and `Output OFF` send `VOLT 0.0` and `OUTP OFF` to the power supply.
