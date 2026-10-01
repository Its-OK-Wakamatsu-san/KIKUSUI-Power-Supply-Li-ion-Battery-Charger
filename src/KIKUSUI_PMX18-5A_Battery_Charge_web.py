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

DEFAULT_INTERVAL_SECONDS = 1.0
DEFAULT_PLOT_INTERVAL_SECONDS = 10.0
DEFAULT_PHASE1_VOLTAGE = 2.8
DEFAULT_PHASE2_VOLTAGE = 4.0
DEFAULT_TRICKLE_CURRENT = 0.01
DEFAULT_CC_CURRENT = 0.5
DEFAULT_PHASE2_MAX_MINUTES = 60.0
DEFAULT_PHASE2_CUTOFF_CURRENT = 0.05
DEFAULT_MAX_HISTORY_POINTS = 36000
SERVER_START_TIME = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
INDEX_HTML_PATH = os.path.join(SCRIPT_DIR, 'templates', 'KIKUSUI_PMX18-5A_Battery_Charge_index.html')
FAVICON_PATH = os.path.join(SCRIPT_DIR, 'BC2.png')

with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as html_file:
    INDEX_HTML = html_file.read().replace('__STARTUP_TIME__', SERVER_START_TIME)


class BatteryChargeWebAdapter:
    def __init__(self):
        self.lock = threading.RLock()
        self.ps = None
        self.resources = []
        self.connected = False
        self.resource = None
        self.logs = []
        self.running = False
        self.paused = False
        self.output_ready = False
        self.remote_enabled = False
        self.stop_event = threading.Event()
        self.worker = None

        self.interval_seconds = DEFAULT_INTERVAL_SECONDS
        self.plot_interval_seconds = DEFAULT_PLOT_INTERVAL_SECONDS
        self.phase1_voltage = DEFAULT_PHASE1_VOLTAGE
        self.phase2_voltage = DEFAULT_PHASE2_VOLTAGE
        self.trickle_current = DEFAULT_TRICKLE_CURRENT
        self.cc_current = DEFAULT_CC_CURRENT
        self.phase2_max_minutes = DEFAULT_PHASE2_MAX_MINUTES
        self.phase2_cutoff_current = DEFAULT_PHASE2_CUTOFF_CURRENT
        self.voltage_protection = 18.0
        self.current_protection = 5.0

        self.phase = 0
        self.phase2_detection_count = 0
        self.phase2_started_elapsed = None
        self.current_requested = 0.0
        self.current_command = 0.0
        self.voltage_command = 0.0
        self.current = 0.0
        self.voltage = 0.0
        self.eps_v = 0.01 #  When charging via a power supply, the voltage of the power supply must be set higher than the battery voltage.
        self.elapsed = 0.0
        self.elapsed_before_run = 0.0
        self.run_started_at = None
        self.pause_started_at = None
        self.paused_seconds = 0.0
        self.history_start_time = SERVER_START_TIME
        self.history = []
        self.next_history_at = time.monotonic() + DEFAULT_PLOT_INTERVAL_SECONDS

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
            if not self.connected:
                self.log('Power supply connection failed.')
            return self.connected
        except Exception as exc:
            self.log(f'Power supply connection check failed: {exc}')
            return False

    def _read_measurements(self):
        if not self.connected:
            self.current = 0.0
            self.voltage = 0.0
            return self.current, self.voltage
        try:
            self.current = float(str(self.ps.Query('MEAS:CURR?')).strip() or 0.0)
            self.voltage = float(str(self.ps.Query('MEAS:VOLT?')).strip() or 0.0)
        except Exception as exc:
            self.log(f'Read error: {exc}')
        return self.current, self.voltage

    def _write(self, command):
        if self.connected:
            self.ps.Write_Command(command)

    def _set_phase(self):
        if self.voltage < self.phase1_voltage:
            self.phase = 0
            self.current_requested = self.trickle_current
        elif self.voltage < self.phase2_voltage:
            self.phase = 1
            self.current_requested = self.cc_current
        else:
            self.current_requested = self.cc_current
            self.phase2_detection_count += 1
            if self.phase2_detection_count > 3:
                if self.phase2_started_elapsed is None:
                    self.phase2_started_elapsed = self.elapsed
                self.phase = 2

        if self.current_requested > self.current_command:
            self.current_command = min(self.current_command + 0.01, self.current_requested)
        elif self.current_requested < self.current_command:
            self.current_command = max(self.current_command - 0.01, self.current_requested)

        self.voltage_command = self.phase2_voltage + self.eps_v   # Slightly above the phase 2 voltage to ensure proper charging behavior
        self._write(f'CURR {self.current_command:.3f}')
        self._write(f'VOLT {self.voltage_command:.3f}')

    def _current_elapsed(self):
        if self.run_started_at is None:
            return self.elapsed_before_run
        paused_seconds = self.paused_seconds
        if self.pause_started_at is not None:
            paused_seconds += time.monotonic() - self.pause_started_at
        return self.elapsed_before_run + time.monotonic() - self.run_started_at - paused_seconds

    def _append_history(self, elapsed):
        self.history.append({
            'time': round(max(0.0, elapsed), 3),
            'currentCommand': round(self.current_command, 6),
            'current': self.current,
            'voltage': self.voltage,
            'phase': self.phase,
        })
        if len(self.history) > DEFAULT_MAX_HISTORY_POINTS:
            del self.history[:-DEFAULT_MAX_HISTORY_POINTS]

    def _control_step(self):
        self._read_measurements()
        self.elapsed = self._current_elapsed()
        self._set_phase()
        now = time.monotonic()
        if now >= self.next_history_at:
            self._append_history(self.elapsed)
            while self.next_history_at <= now:
                self.next_history_at += self.plot_interval_seconds
        if self.phase == 2:
            phase2_minutes = max(
                0.0, (self.elapsed - self.phase2_started_elapsed) / 60.0
            )
            time_limit_reached = phase2_minutes >= self.phase2_max_minutes
            current_limit_reached = self.current < self.phase2_cutoff_current
            if time_limit_reached or current_limit_reached:
                reasons = []
                if time_limit_reached:
                    reasons.append(
                        f'time limit reached ({phase2_minutes:.2f} >= '
                        f'{self.phase2_max_minutes:g} min)'
                    )
                if current_limit_reached:
                    reasons.append(
                        f'current below threshold ({self.current:.4f} < '
                        f'{self.phase2_cutoff_current:g} A)'
                    )
                self._stop_locked('Charge completed: ' + '; '.join(reasons) + '.')

    def _control_loop(self, stop_event):
        while not stop_event.wait(self.interval_seconds):
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
                    self._require_connection()
                    self._write('SYST:REMOTE')
                    self.remote_enabled = True
                    self.log('Remote mode enabled.')
                    return {'ok': True, 'message': 'Remote mode enabled'}
                if action == 'local':
                    self._require_connection()
                    self._write('SYST:LOCAL')
                    self.remote_enabled = False
                    self.log('Local mode enabled.')
                    return {'ok': True, 'message': 'Local mode enabled'}
                if action == 'ready':
                    self._require_connection()
                    self._write('OUTP ON')
                    self.output_ready = True
                    self.log('Power supply output enabled.')
                    return {'ok': True, 'message': 'Output enabled'}
                if action == 'disable':
                    self._require_connection()
                    if self.running:
                        self._stop_locked('Charge stopped because output was disabled.')
                    self._write('VOLT 0.0')
                    self._write('OUTP OFF')
                    self.output_ready = False
                    self.log('Power supply output disabled.')
                    return {'ok': True, 'message': 'Output disabled'}
                if action == 'start':
                    return self._start_locked()
                if action == 'pause_resume':
                    return self._pause_resume_locked()
                if action == 'stop':
                    self._stop_locked('Charge stopped')
                    return {'ok': True, 'message': 'Charge stopped'}
                if action == 'reset':
                    self._reset_locked()
                    return {'ok': True, 'message': 'Elapsed time and history reset'}
                if action == 'set_config':
                    self._apply_config_locked(data)
                    if self.running:
                        self.next_history_at = time.monotonic() + self.plot_interval_seconds
                    self.log(
                        'Charge settings applied: '
                        f'interval={self.interval_seconds:g}s, '
                        f'plot_interval={self.plot_interval_seconds:g}s, '
                        f'phase1_voltage={self.phase1_voltage:g}V, '
                        f'phase2_voltage={self.phase2_voltage:g}V, '
                        f'trickle_current={self.trickle_current:g}A, '
                        f'cc_current={self.cc_current:g}A, '
                        f'phase2_max={self.phase2_max_minutes:g}min, '
                        f'cutoff_current={self.phase2_cutoff_current:g}A.'
                    )
                    return {
                        'ok': True,
                        'message': (
                            f'Charge settings updated: control={self.interval_seconds:g}s, '
                            f'plot/output={self.plot_interval_seconds:g}s'
                        ),
                    }
                if action == 'measure':
                    self._read_measurements()
                    return {'ok': True, 'message': 'Measurement updated'}
                if action == 'set_voltage_protection':
                    self._set_protection_locked('voltage', data.get('protectionVoltage'))
                    return {'ok': True, 'message': f'Voltage protection set to {self.voltage_protection:g} V'}
                if action == 'set_current_protection':
                    self._set_protection_locked('current', data.get('protectionCurrent'))
                    return {'ok': True, 'message': f'Current protection set to {self.current_protection:g} A'}
                return {'ok': False, 'message': f'Unknown action: {action}'}
        except Exception as exc:
            self.log(f'Command error: {exc}')
            return {'ok': False, 'message': str(exc)}

    def _require_connection(self):
        if not self.connected:
            raise RuntimeError('No device connected. Connect the power supply first.')

    def _start_locked(self):
        self._require_connection()
        if not self.output_ready:
            raise RuntimeError('Press Output ON before starting charge.')
        if self.running:
            return {'ok': True, 'message': 'Charge is already running'}
        self._apply_config_locked({})
        self.running = True
        self.paused = False
        self.phase = 0
        self.phase2_detection_count = 0
        self.phase2_started_elapsed = None
        self.current_command = 0.0
        self.current_requested = 0.0
        self.elapsed_before_run = 0.0
        self.elapsed = 0.0
        self.run_started_at = time.monotonic()
        self.pause_started_at = None
        self.paused_seconds = 0.0
        self.history_start_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        self.history.clear()
        self.next_history_at = time.monotonic() + self.plot_interval_seconds
        self._read_measurements()
        self._append_history(0.0)
        self.stop_event = threading.Event()
        worker_stop_event = self.stop_event
        self.worker = threading.Thread(
            target=self._control_loop,
            args=(worker_stop_event,),
            name='battery-charge-control',
            daemon=True,
        )
        self.worker.start()
        self.log('Charge started.')
        return {'ok': True, 'message': 'Charge started'}

    def _pause_resume_locked(self):
        if not self.running:
            raise RuntimeError('Charge is not running.')
        if self.paused:
            self.paused_seconds += time.monotonic() - self.pause_started_at
            self.pause_started_at = None
            self.paused = False
            self.log('Charge resumed.')
            return {'ok': True, 'message': 'Charge resumed'}
        self.paused = True
        self.pause_started_at = time.monotonic()
        self.elapsed = self._current_elapsed()
        self.log('Charge paused.')
        return {'ok': True, 'message': 'Charge paused'}

    def _reset_locked(self):
        now = time.monotonic()
        self.elapsed = 0.0
        self.elapsed_before_run = 0.0
        self.paused_seconds = 0.0
        self.phase = 0
        self.phase2_detection_count = 0
        self.phase2_started_elapsed = None
        self.history_start_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        self.history.clear()
        self.next_history_at = now + self.plot_interval_seconds

        if self.running:
            self.run_started_at = now
            self.pause_started_at = now if self.paused else None
            self._read_measurements()
            self._append_history(0.0)

        self.log('Elapsed time and history reset.')

    def _stop_locked(self, message):
        if self.run_started_at is not None:
            self.elapsed = self._current_elapsed()
            self.elapsed_before_run = self.elapsed
        self.running = False
        self.paused = False
        self.pause_started_at = None
        self.stop_event.set()
        self.run_started_at = None
        self.elapsed_before_run = self.elapsed
        self._write('VOLT 0.0')
        self._write('OUTP OFF')
        self.output_ready = False
        self.log(message)

    def _apply_config_locked(self, data):
        self.interval_seconds = max(float(data.get('intervalSeconds', self.interval_seconds)), 0.1)
        self.plot_interval_seconds = max(float(data.get('plotIntervalSeconds', self.plot_interval_seconds)), 0.1)
        self.phase1_voltage = float(data.get('phase1Voltage', self.phase1_voltage))
        self.phase2_voltage = float(data.get('phase2Voltage', self.phase2_voltage))
        self.trickle_current = float(data.get('trickleCurrent', self.trickle_current))
        self.cc_current = float(data.get('ccCurrent', self.cc_current))
        self.phase2_max_minutes = max(float(data.get('phase2MaxMinutes', self.phase2_max_minutes)), 0.0)
        self.phase2_cutoff_current = max(float(data.get('phase2CutoffCurrent', self.phase2_cutoff_current)), 0.0)

    def _set_protection_locked(self, kind, value):
        self._require_connection()
        limit = float(value)
        if limit <= 0:
            raise ValueError('Protection limit must be greater than 0.')
        if kind == 'voltage':
            self._write(f'VOLT:PROT {limit:g}')
            self.voltage_protection = limit
            self.log(f'Voltage protection set to {limit:g} V.')
        else:
            self._write(f'CURR:PROT {limit:g}')
            self.current_protection = limit
            self.log(f'Current protection set to {limit:g} A.')

    def snapshot(self):
        with self.lock:
            if self.running:
                self.elapsed = self._current_elapsed()
            return {
                'connected': self.connected,
                'resource': self.resource,
                'resources': self.resources,
                'remoteEnabled': self.remote_enabled,
                'outputReady': self.output_ready,
                'running': self.running,
                'paused': self.paused,
                'phase': self.phase,
                'currentRequested': self.current_requested,
                'currentCommand': self.current_command,
                'current': self.current,
                'voltage': self.voltage,
                'voltageCommand': self.voltage_command,
                'elapsed': self.elapsed,
                'historyStartTime': self.history_start_time,
                'history': list(self.history),
                'log': list(self.logs),
                'config': {
                    'intervalSeconds': self.interval_seconds,
                    'plotIntervalSeconds': self.plot_interval_seconds,
                    'phase1Voltage': self.phase1_voltage,
                    'phase2Voltage': self.phase2_voltage,
                    'trickleCurrent': self.trickle_current,
                    'ccCurrent': self.cc_current,
                    'phase2MaxMinutes': self.phase2_max_minutes,
                    'phase2CutoffCurrent': self.phase2_cutoff_current,
                    'voltageProtection': self.voltage_protection,
                    'currentProtection': self.current_protection,
                },
            }


adapter = BatteryChargeWebAdapter()


class DashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, format_string, *args):
        return

    def _send_json(self, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/favicon.png':
            with open(FAVICON_PATH, 'rb') as icon_file:
                content = icon_file.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(content)
            return
        if parsed.path == '/':
            content = INDEX_HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if parsed.path == '/api/status':
            self._send_json(adapter.snapshot())
            return
        self.send_error(404, 'Not found')

    def do_POST(self):
        if urlparse(self.path).path != '/api/command':
            self.send_error(404, 'Not found')
            return
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length)
        data = json.loads(body.decode('utf-8') or '{}')
        result = adapter.dispatch(data.get('action'), data)
        self._send_json(result)


async def ws_server():
    async def handler(ws):
        try:
            while True:
                await asyncio.sleep(1.0)
                await ws.send(json.dumps(adapter.snapshot()))
        except Exception:
            pass

    async with websockets.serve(handler, '127.0.0.1', 8004):
        await asyncio.Future()


def run_http_server():
    port = int(os.environ.get('KIKUSUI_BATTERY_PORT', '8003'))
    server = ThreadingHTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f'HTTP URL: http://localhost:{port}')
    print('WS URL: ws://localhost:8004')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        adapter.dispatch('stop')
        try:
            adapter.dispatch('disable')
        except Exception:
            pass
    finally:
        server.server_close()


def main():
    http_thread = threading.Thread(target=run_http_server, name='battery-charge-http', daemon=True)
    http_thread.start()
    asyncio.run(ws_server())


if __name__ == '__main__':
    main()
