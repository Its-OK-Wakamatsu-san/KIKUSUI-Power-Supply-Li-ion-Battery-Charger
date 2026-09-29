# KIKUSUI PMX18-5A CV Control　etc.

There are the web-based CV control and  Battery charger versions,  and Tkinter/Matplotlib versions(old versions).

## Constant-voltage Web UI
The Tkinter program `KIKUSUI_PMX18-5A_CNTL.py` also has a WebSocket-based HTML version.

1. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_CNTL_web.py"
   ```
2. Open the browser at:
   ```text
   http://localhost:8001
   ```
3. Select the VISA resource, press `Remote`, press `Output ON`, apply the voltage settings, and press `Start`.
   
## Battery charge Web UI
The Tkinter program `KIKUSUI_PMX18-5A_Battery_Charge.py` has a WebSocket-based Web UI version.
1. Run:
   ```powershell
   python "C:\Users\directory\KIKUSUI_PMX18-5A_Battery_Charge_web.py
   ```
2. Open the browser at:
   ```text
   http://localhost:8003
   ```
3. Select the VISA resource, press `Remote`, press `Output ON`, apply the charge settings, and press `Start`.

## Features


