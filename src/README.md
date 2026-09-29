# KIKUSUI PMX18-5A CV Control　etc.

There are the web-based CV control and  Battery charger versions,  and Tkinter/Matplotlib versions(old versions).

## deifinition

1. web-based CV control.
2. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
3. Open the browser at:
   ```text
   http://localhost:8001
   ```
   
1.  web-based CV control.
2. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
3. Open the browser at:
   ```text
   http://localhost:8001
   ```
   On the page, press the control buttons in this order:
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
- Libraries: pyvisa, http, urllib, websocket
- VISA backend: NI-VISA or compatible driver

## Related resources
- [Kikusui PMX-A Series](https://kikusui.co.jp/w2-2/dc-power-supply/pmx-a/pmx-a/)
- [Kikusui Sample Code for Python](https://kikusui.co.jp/download/python/)
- [NI-VISA](https://www.ni.com/ja-jp/support/downloads/drivers/download.ni-visa.html#346210)

## Battery charge Web UI

This battery charger is a WebSocket-based Web UI version.

1. Run `KIKUSUI_PMX18-5A_Battery_Charge_web.bat`, or run `KIKUSUI_PMX18-5A_Battery_Charge_web.py` from this folder.
2. Open `http://localhost:8003` in a browser.
3. Select the VISA resource, press `Remote`, press `Output ON`, apply the charge settings, and press `Start`.

The HTTP server uses port `8003` and the WebSocket server uses port `8004`. The browser receives live status once per second over WebSocket. The control interval defaults to 1 second; the graph and CSV history interval defaults to 10 seconds and can be changed independently.

The current command is ramped in 0.01 A steps and sent to the power supply with `CURR` commands. The second tab sends `VOLT:PROT` and `CURR:PROT` protection-limit commands. `Pause / Resume` excludes paused time from elapsed charge time. `RESET` clears elapsed time and history without switching the output. `Stop` and `Output OFF` send `VOLT 0.0` and `OUTP OFF`.

## Constant-voltage Web UI

The Tkinter program `KIKUSUI_PMX18-5A_CNTL.py` also has a WebSocket-based HTML version.

1. Run `KIKUSUI_PMX18-5A_CNTL_web.bat`.
2. Open `http://localhost:8005` in a browser.
3. Select the VISA resource, enable Remote and Output, set the target voltage, and press `Start`.

The control screen supports manual voltage ramping at 0.1 V per control step, Pause/Resume, RESET, CSV history, voltage/current protection limits, and one-second WebSocket status updates. The HTTP server uses port `8005` and the WebSocket server uses port `8006`.
