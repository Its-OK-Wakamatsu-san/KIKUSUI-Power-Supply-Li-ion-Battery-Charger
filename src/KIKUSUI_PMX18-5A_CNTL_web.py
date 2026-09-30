import asyncio
import json
import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

import websockets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import KIKUSUI_PMX18_5A_module

DEFAULT_CONTROL_INTERVAL = 0.5
DEFAULT_HISTORY_INTERVAL = 10.0
DEFAULT_MAX_HISTORY = 36000
VOLTAGE_RATING = 18.0
CURRENT_RATING = 5.0
SERVER_START_TIME = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
INDEX_HTML_PATH = os.path.join(SCRIPT_DIR, 'templates', 'KIKUSUI_PMX18-5A_CNTL_index.html')
FAVICON_PATH = os.path.join(SCRIPT_DIR, 'CV2.png')
with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as html_file:
    INDEX_HTML = html_file.read().replace('__STARTUP_TIME__', SERVER_START_TIME)


class ConstantVoltageWebAdapter:
    def __init__(self):
        self.lock = threading.RLock()
        self.ps = None
        self.resources = []
        self.resource = None
        self.connected = False
        self.logs = []
        self.remote_enabled = False
        self.output_ready = False
        self.running = False
        self.paused = False
        self.manual_mode = True
        self.stop_event = threading.Event()
        self.worker = None

        self.control_interval = DEFAULT_CONTROL_INTERVAL
        self.history_interval = DEFAULT_HISTORY_INTERVAL
        self.max_history = DEFAULT_MAX_HISTORY
        self.manual_voltage = 7.8
        self.target_voltage = 0.0
        self.command_voltage = 0.0
        self.ramp_rate = 0.1
        self.current = 0.0
        self.voltage = 0.0
        self.elapsed = 0.0
        self.run_started_at = None
        self.paused_seconds = 0.0
        self.pause_started_at = None
        self.next_history_at = time.monotonic() + self.history_interval
        self.history_start_time = SERVER_START_TIME
        self.history = []
        self.voltage_protection_percent = 105.0
        self.current_protection_percent = 105.0
        self.voltage_protection = 18.9
        self.current_protection = 5.25

        try:
            self.ps = KIKUSUI_PMX18_5A_module.Application()
        except Exception as exc:
            self.log(f'VISA initialization failed: {exc}')
        self._discover_and_connect()

    def log(self, message):
        if message:
            with self.lock:
                self.logs.append(str(message))
                self.logs = self.logs[-60:]

    def _discover_and_connect(self, resource=None):
        if self.ps is None:
            return False
        try:
            self.resources = list(self.ps.get_resources() or [])
            selected = resource or (self.resources[0] if self.resources else None)
            if not selected or selected == 'None':
                self.log('No KIKUSUI resource was found.')
                return False
            ok, message = self.ps.Open(selected)
            self.connected = bool(ok)
            self.resource = selected if self.connected else None
            self.log(message)
            return self.connected
        except Exception as exc:
            self.log(f'Connection check failed: {exc}')
            return False

    def _require_connection(self):
        if not self.connected:
            raise RuntimeError('No device connected.')

    def _write(self, command):
        if self.connected:
            self.ps.Write_Command(command)

    def _read(self):
        if not self.connected:
            self.current = self.voltage = 0.0
            return
        try:
            self.current = float(str(self.ps.Query('MEAS:CURR?')).strip() or 0.0)
            self.voltage = float(str(self.ps.Query('MEAS:VOLT?')).strip() or 0.0)
        except Exception as exc:
            self.log(f'Read error: {exc}')

    def _elapsed_now(self):
        if self.run_started_at is None:
            return self.elapsed
        paused = self.paused_seconds
        if self.pause_started_at is not None:
            paused += time.monotonic() - self.pause_started_at
        return max(0.0, time.monotonic() - self.run_started_at - paused)

    def _append_history(self):
        self.history.append({
            'time': round(self.elapsed, 3),
            'targetVoltage': round(self.target_voltage, 3),
            'commandVoltage': round(self.command_voltage, 3),
            'voltage': self.voltage,
            'current': self.current,
        })
        if len(self.history) > self.max_history:
            del self.history[:-self.max_history]

    def _apply_voltage_step(self):
        target = self.manual_voltage if self.manual_mode else self.target_voltage
        self.target_voltage = target
        delta = target - self.command_voltage
        step = self.ramp_rate
        if abs(delta) <= step:
            self.command_voltage = target
        else:
            self.command_voltage += step if delta > 0 else -step
        self._write(f'VOLT {self.command_voltage:.3f}')

    def _control_step(self):
        self._apply_voltage_step()
        self._read()
        self.elapsed = self._elapsed_now()
        now = time.monotonic()
        if now >= self.next_history_at:
            self._append_history()
            while self.next_history_at <= now:
                self.next_history_at += self.history_interval

    def _control_loop(self, stop_event):
        while not stop_event.wait(self.control_interval):
            with self.lock:
                if stop_event is not self.stop_event:
                    return
                if not self.running or self.paused or not self.output_ready:
                    continue
                try:
                    self._control_step()
                except Exception as exc:
                    self.log(f'Control error: {exc}')
                    self._stop_locked('Control error')

    def dispatch(self, action, data=None):
        data = data or {}
        try:
            with self.lock:
                if action == 'connect':
                    ok = self._discover_and_connect(data.get('resource'))
                    return {'ok': ok, 'message': 'Connected' if ok else 'Connection failed'}
                if action == 'remote_on':
                    self._require_connection(); self._write('SYST:REMOTE'); self.remote_enabled = True
                    self.log('Remote mode enabled.'); return {'ok': True, 'message': 'Remote mode enabled'}
                if action == 'local':
                    self._require_connection(); self._write('SYST:LOCAL'); self.remote_enabled = False
                    self.log('Local mode enabled.'); return {'ok': True, 'message': 'Local mode enabled'}
                if action == 'ready':
                    self._require_connection(); self._write('CURR 0.001'); self._write('OUTP ON'); self._write('VOLT 0.0')
                    self.output_ready = True; self.log('Power supply ready.'); return {'ok': True, 'message': 'Output enabled'}
                if action == 'disable':
                    self._stop_locked('Output disabled'); return {'ok': True, 'message': 'Output disabled'}
                if action == 'start':
                    return self._start_locked()
                if action == 'stop':
                    self._stop_locked('Control stopped'); return {'ok': True, 'message': 'Control stopped'}
                if action == 'pause_resume':
                    return self._pause_resume_locked()
                if action == 'reset_time':
                    self._reset_locked(); return {'ok': True, 'message': 'Time and history reset'}
                if action == 'set_voltage':
                    self.manual_voltage = abs(float(data.get('voltage', 0.0)))
                    self.manual_mode = True; self.target_voltage = self.manual_voltage
                    self.log(f'Manual target voltage set to {self.manual_voltage:.3f} V.')
                    return {'ok': True, 'message': 'Voltage target updated'}
                if action == 'manual_mode':
                    self.manual_mode = not self.manual_mode
                    self.log(f'Manual mode: {self.manual_mode}.')
                    return {'ok': True, 'message': 'Manual mode enabled' if self.manual_mode else 'Manual mode disabled'}
                if action == 'set_config':
                    self.control_interval = max(float(data.get('controlInterval', self.control_interval)), 0.1)
                    self.history_interval = max(float(data.get('historyInterval', self.history_interval)), 0.1)
                    self.manual_voltage = abs(float(data.get('targetVoltage', self.manual_voltage)))
                    self.target_voltage = self.manual_voltage
                    self.next_history_at = time.monotonic() + self.history_interval
                    self.log(f'Settings applied: control={self.control_interval:g}s, plot/output={self.history_interval:g}s, target={self.manual_voltage:g}V.')
                    return {'ok': True, 'message': f'Settings applied: control={self.control_interval:g}s, plot/output={self.history_interval:g}s, target={self.manual_voltage:g}V'}
                if action == 'set_voltage_protection_percent':
                    self._set_protection_locked('voltage', data, from_percent=True)
                    return {'ok': True, 'message': f'Voltage protection set to {self.voltage_protection:g} V'}
                if action == 'set_voltage_protection':
                    self._set_protection_locked('voltage', data)
                    return {'ok': True, 'message': f'Voltage protection set to {self.voltage_protection:g} V'}
                if action == 'set_current_protection_percent':
                    self._set_protection_locked('current', data, from_percent=True)
                    return {'ok': True, 'message': f'Current protection set to {self.current_protection:g} A'}
                if action == 'set_current_protection':
                    self._set_protection_locked('current', data)
                    return {'ok': True, 'message': f'Current protection set to {self.current_protection:g} A'}
                if action == 'measure':
                    self._read(); return {'ok': True, 'message': 'Measurement updated'}
                return {'ok': False, 'message': f'Unknown action: {action}'}
        except Exception as exc:
            self.log(f'Command error: {exc}')
            return {'ok': False, 'message': str(exc)}

    def _start_locked(self):
        self._require_connection()
        if not self.output_ready:
            raise RuntimeError('Press Output ON before Start.')
        if self.running:
            return {'ok': True, 'message': 'Already running'}
        self.running = True; self.paused = False; self.elapsed = 0.0
        self.run_started_at = time.monotonic(); self.paused_seconds = 0.0; self.pause_started_at = None
        self.command_voltage = 0.0; self.target_voltage = self.manual_voltage if self.manual_mode else self.target_voltage
        self.history.clear(); self.history_start_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        self.next_history_at = time.monotonic() + self.history_interval
        self._read(); self._append_history()
        self.stop_event = threading.Event(); event = self.stop_event
        self.worker = threading.Thread(target=self._control_loop, args=(event,), name='cv-control', daemon=True)
        self.worker.start(); self.log('Control started.')
        return {'ok': True, 'message': 'Control started'}

    def _pause_resume_locked(self):
        if not self.running:
            raise RuntimeError('Control is not running.')
        if self.paused:
            self.paused_seconds += time.monotonic() - self.pause_started_at; self.pause_started_at = None; self.paused = False
            self.log('Control resumed.'); return {'ok': True, 'message': 'Resumed'}
        self.paused = True; self.pause_started_at = time.monotonic(); self.elapsed = self._elapsed_now()
        self.log('Control paused.'); return {'ok': True, 'message': 'Paused'}

    def _reset_locked(self):
        self.elapsed = 0.0; self.history.clear(); self.history_start_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        self.paused_seconds = 0.0; self.next_history_at = time.monotonic() + self.history_interval
        if self.running:
            self.run_started_at = time.monotonic(); self.pause_started_at = self.run_started_at if self.paused else None; self._read(); self._append_history()
        self.log('Time and history reset.')

    def _stop_locked(self, message):
        self.running = False; self.paused = False; self.pause_started_at = None; self.stop_event.set()
        self._write('VOLT 0.0'); self._write('OUTP OFF'); self.output_ready = False; self.log(message)

    def _set_protection_locked(self, kind, data, from_percent=False):
        self._require_connection()
        if kind == 'voltage':
            if from_percent:
                percent = float(data.get('voltageProtectionPercent', self.voltage_protection_percent))
                limit = VOLTAGE_RATING * percent / 100.0
            else:
                percent = self.voltage_protection_percent
                limit = float(data.get('voltageProtection', self.voltage_protection))
            if percent <= 0 or limit <= 0:
                raise ValueError('Voltage protection values must be greater than 0.')
            self._write(f'VOLT:PROT {limit:g}')
            self.voltage_protection_percent = percent
            self.voltage_protection = limit
            self.log(f'Voltage protection applied: {limit:g} V ({percent:g}%).')
            return

        if from_percent:
            percent = float(data.get('currentProtectionPercent', self.current_protection_percent))
            limit = CURRENT_RATING * percent / 100.0
        else:
            percent = self.current_protection_percent
            limit = float(data.get('currentProtection', self.current_protection))
        if percent <= 0 or limit <= 0:
            raise ValueError('Current protection values must be greater than 0.')
        self._write(f'CURR:PROT {limit:g}')
        self.current_protection_percent = percent
        self.current_protection = limit
        self.log(f'Current protection applied: {limit:g} A ({percent:g}%).')

    def snapshot(self):
        with self.lock:
            if self.running: self.elapsed = self._elapsed_now()
            return {
                'connected': self.connected, 'resource': self.resource, 'resources': self.resources,
                'remoteEnabled': self.remote_enabled, 'outputReady': self.output_ready,
                'running': self.running, 'paused': self.paused, 'manualMode': self.manual_mode,
                'voltage': self.voltage, 'current': self.current, 'elapsed': self.elapsed,
                'targetVoltage': self.target_voltage, 'commandVoltage': self.command_voltage,
                'historyStartTime': self.history_start_time, 'history': list(self.history), 'log': list(self.logs),
                'config': {
                    'controlInterval': self.control_interval, 'historyInterval': self.history_interval,
                    'targetVoltage': self.manual_voltage, 'rampRate': self.ramp_rate,
                    'voltageProtectionPercent': self.voltage_protection_percent,
                    'currentProtectionPercent': self.current_protection_percent,
                    'voltageProtection': self.voltage_protection, 'currentProtection': self.current_protection,
                },
            }


adapter = ConstantVoltageWebAdapter()


class DashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, format_string, *args):
        return

    def _json(self, value):
        payload = json.dumps(value).encode('utf-8'); self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/favicon.png':
            with open(FAVICON_PATH, 'rb') as icon_file:
                content = icon_file.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(content)
            return
        if path == '/':
            content = INDEX_HTML.encode('utf-8'); self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(content))); self.end_headers(); self.wfile.write(content); return
        if path == '/api/status': self._json(adapter.snapshot()); return
        self.send_error(404, 'Not found')

    def do_POST(self):
        if urlparse(self.path).path != '/api/command': self.send_error(404, 'Not found'); return
        length = int(self.headers.get('Content-Length', '0')); data = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
        self._json(adapter.dispatch(data.get('action'), data))


async def ws_server():
    async def handler(ws):
        try:
            while True:
                await asyncio.sleep(1.0); await ws.send(json.dumps(adapter.snapshot()))
        except Exception:
            pass
    async with websockets.serve(handler, '127.0.0.1', 8002):
        await asyncio.Future()


def run_http_server():
    port = int(os.environ.get('KIKUSUI_CNTL_PORT', '8001'))
    server = ThreadingHTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f'HTTP URL: http://localhost:{port}'); print('WS URL: ws://localhost:8002')
    try: server.serve_forever()
    except KeyboardInterrupt:
        try: adapter.dispatch('stop')
        except Exception: pass
    finally: server.server_close()


def main():
    threading.Thread(target=run_http_server, name='cv-http', daemon=True).start(); asyncio.run(ws_server())


if __name__ == '__main__':
    main()
