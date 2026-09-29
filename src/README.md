# KIKUSUI PMX18-5A CV Control　etc.

There are the web-based CV control and  Battery charger versions,  and Tkinter/Matplotlib versions(old versions).

## Usage
### web-based CV control

1. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
2. Open the browser at:
   ```text
   http://localhost:8001
   ```
3. Select the VISA resource, press `Remote`, press `Output ON`, apply the voltage settings, and press `Start`.
   
### web-based Battery charger
1. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
2. Open the browser at:
   ```text
   http://localhost:8003
   ```
3. Select the VISA resource, press `Remote`, press `Output ON`, apply the charge settings, and press `Start`.

## Features


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
