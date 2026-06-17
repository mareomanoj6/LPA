import os
import sys
import json
import socket
import threading
import subprocess
import tempfile

from gi.repository import GLib


class TrayIcon:

    def __init__(self, app_dir: str, on_show: callable, on_quit: callable):
        self.app_dir    = app_dir
        self._on_show   = on_show
        self._on_quit   = on_quit
        self._proc      = None
        self._conn      = None
        self._sock      = None
        self._sock_path = None
        self._shutting_down = False

        self._start_tray()
        
        GLib.timeout_add(2000, self._watchdog_tick)

    def _start_tray(self):
        if self._shutting_down:
            return

        icon_path        = os.path.join(self.app_dir, 'assets', 'logo.png')
        tray_script      = os.path.join(self.app_dir, 'tray', 'tray_process.py')

        if not os.path.exists(tray_script):
            print('[TrayIcon] tray_process.py not found – tray disabled.')
            return

        self._sock_path = os.path.join(
            tempfile.gettempdir(), f'lpa_tray_{os.getpid()}.sock'
        )
        
        if os.path.exists(self._sock_path):
            try:
                os.remove(self._sock_path)
            except Exception:
                pass

        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.bind(self._sock_path)
            self._sock.listen(1)
        except Exception as e:
            print(f'[TrayIcon] Could not create socket: {e} – tray disabled.')
            self._cleanup_socket()
            return

        try:
            self._proc = subprocess.Popen(
                [sys.executable, tray_script, self._sock_path, icon_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f'[TrayIcon] Could not start tray subprocess: {e} – tray disabled.')
            self._cleanup_socket()
            return

        self._sock.settimeout(5.0)
        try:
            self._conn, _ = self._sock.accept()
            self._conn.settimeout(None)
        except socket.timeout:
            print('[TrayIcon] Tray subprocess did not connect in time – tray disabled.')
            self._kill_proc()
            self._cleanup_socket()
            return
        except Exception as e:
            print(f'[TrayIcon] Socket accept failed: {e} – tray disabled.')
            self._kill_proc()
            self._cleanup_socket()
            return

        print('[TrayIcon] Tray subprocess connected.')

        t = threading.Thread(target=self._reader_loop, daemon=True, name='tray-reader')
        t.start()

    def _watchdog_tick(self) -> bool:
        if self._shutting_down:
            return GLib.SOURCE_REMOVE
            
        if self._proc is not None:
            ret = self._proc.poll()
            if ret is not None:
                if ret == 2:
                    print('[TrayIcon] Watchdog: Tray unsupported by host environment. Disabling tray.', flush=True)
                    self._shutting_down = True
                    self._cleanup_socket()
                    return GLib.SOURCE_REMOVE
                    
                print(f'[TrayIcon] Watchdog: Subprocess died (exit code {ret}). Restarting...', flush=True)
                self._kill_proc()
                self._cleanup_socket()
                self._start_tray()
                
        return GLib.SOURCE_CONTINUE

    def _reader_loop(self):
        buf = ''
        while True:
            try:
                chunk = self._conn.recv(256).decode()
                if not chunk:
                    break
                buf += chunk
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg   = json.loads(line)
                        event = msg.get('event')
                        if event == 'show':
                            GLib.idle_add(self._on_show)
                        elif event == 'quit':
                            GLib.idle_add(self._on_quit)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    def _send(self, msg: dict):
        if self._conn is None:
            return
        try:
            self._conn.sendall((json.dumps(msg) + '\n').encode())
        except Exception:
            pass

    def shutdown(self) -> None:
        self._shutting_down = True
        self._send({'cmd': 'quit'})
        self._kill_proc()
        self._cleanup_socket()

    def _kill_proc(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def _cleanup_socket(self):
        for obj in (self._conn, self._sock):
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
        if self._sock_path and os.path.exists(self._sock_path):
            try:
                os.remove(self._sock_path)
            except Exception:
                pass
        self._conn = self._sock = self._sock_path = None

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass
