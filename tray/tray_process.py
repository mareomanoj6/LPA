#!/usr/bin/env python3
import sys
import os
import json
import socket
import threading
import signal

import gi

try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ImportError, ValueError):
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3
    except (ImportError, ValueError):
        print('[tray_process] No AppIndicator3 available. Exiting.', flush=True)
        sys.exit(1)

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib


def main():
    if len(sys.argv) < 3:
        print('[tray_process] Usage: tray_process.py <socket_path> <icon_path>', flush=True)
        sys.exit(1)

    socket_path = sys.argv[1]
    icon_path   = sys.argv[2]

    try:
        indicator = AppIndicator3.Indicator.new(
            'LPA',
            'io.github.mareomanoj6.lpa',
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_title('LPA')
    except Exception as e:
        print(f'[tray_process] Tray not supported or failed to init: {e}', flush=True)
        sys.exit(2)

    is_flatpak = os.path.exists('/.flatpak-info')
    if is_flatpak:
        indicator.set_icon_full('io.github.mareomanoj6.lpa', 'LPA')
    elif os.path.exists(icon_path):
        try:
            indicator.set_icon_full(icon_path, 'LPA')
        except Exception:
            pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(socket_path)
    except Exception as e:
        print(f'[tray_process] Cannot connect to socket {socket_path}: {e}', flush=True)
        sys.exit(1)

    def send_event(event: str):
        """Send an event back to the main process."""
        try:
            msg = json.dumps({'event': event}) + '\n'
            sock.sendall(msg.encode())
        except Exception:
            pass

    menu = Gtk.Menu()

    item_show = Gtk.MenuItem(label='Show LPA')
    item_show.connect('activate', lambda _: send_event('show'))
    menu.append(item_show)

    sep = Gtk.SeparatorMenuItem()
    menu.append(sep)

    item_quit = Gtk.MenuItem(label='Quit')
    item_quit.connect('activate', lambda _: send_event('quit'))
    menu.append(item_quit)

    menu.show_all()
    indicator.set_menu(menu)

    def _reader():
        buf = ''
        while True:
            try:
                chunk = sock.recv(1024).decode()
                if not chunk:
                    break
                buf += chunk
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        cmd = msg.get('cmd')
                        if cmd == 'quit':
                            GLib.idle_add(Gtk.main_quit)
                            return
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break
        GLib.idle_add(Gtk.main_quit)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    signal.signal(signal.SIGTERM, lambda *_: Gtk.main_quit())

    Gtk.main()
    sock.close()


if __name__ == '__main__':
    main()
