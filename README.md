# KIKUSUI PMX18-5A Web CV Control

This project is the main web-based CV control panel for the KIKUSUI PMX18-5A power supply.

## Main startup flow

1. Open a terminal in the project folder.
2. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
3. Open the browser at:
   ```text
   http://localhost:8001
   ```
4. On the page, press the control buttons in this order:
   - Set the target voltage
   - Remote ON
   - Output ON
   - Monitor the live graph and log
5. To stop, press Output OFF or end the server with Ctrl+C.

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

## Battery charge Web UI

The Tkinter/Matplotlib battery charger has a WebSocket-based Web UI version.
<img width="1550" height="1142" alt="image" src="https://github.com/user-attachments/assets/e74a4a95-9f6f-4997-aca4-e14093017a2e" />

1. Run `KIKUSUI_PMX18-5A_Battery_Charge_web.py` from this folder.
2. Open `http://localhost:8003` in a browser.
3. Connect the VISA resource, enable Remote and Output, then press Start.

The browser receives measurements, charge phase, logs, and graph history over WebSocket once per second. Pause/Resume excludes the paused time from elapsed charge time. `Stop` and `Output OFF` send `VOLT 0.0` and `OUTP OFF` to the power supply.
