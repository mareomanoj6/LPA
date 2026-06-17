#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio, GLib

try:
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
except Exception:
    Notify = None

import os
import sys
import signal
import atexit

from data.state import State
from audio.player import LoFiPlayer, AmbiencePlayer
from ui.main_window import MainWindow
from tray.tray_icon import TrayIcon

APP_DIR: str = os.path.dirname(os.path.abspath(__file__))


_XDG_DATA_HOME: str = os.environ.get("XDG_DATA_HOME", "").strip() or os.path.expanduser("~/.local/share")
_DATA_DIR: str = os.path.join(_XDG_DATA_HOME, 'lpa')
PID_FILE: str = os.path.join(_DATA_DIR, 'lpa.pid')

def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _enforce_single_instance() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as fh:
                existing_pid = int(fh.read().strip())
        except (ValueError, OSError):
            existing_pid = None

        if existing_pid is not None and existing_pid != os.getpid() and _pid_is_running(existing_pid):
            print(
                f'[lpa] Another instance is already running (PID {existing_pid}). '
                'Sending SIGUSR1 to show its window and exiting.'
            )
            try:
                os.kill(existing_pid, signal.SIGUSR1)
            except OSError as exc:
                print(f'[lpa] Could not signal existing instance: {exc}')
            sys.exit(0)
        else:
            _remove_pid_file()

    try:
        with open(PID_FILE, 'w') as fh:
            fh.write(str(os.getpid()))
    except OSError as exc:
        print(f'[lpa] Warning: could not write PID file: {exc}')

    atexit.register(_remove_pid_file)


def _remove_pid_file() -> None:
    if not os.path.exists(PID_FILE):
        return
    try:
        with open(PID_FILE, 'r') as fh:
            stored_pid = int(fh.read().strip())
        if stored_pid == os.getpid():
            os.remove(PID_FILE)
    except Exception:
        pass

def _on_sigusr1(window: MainWindow) -> bool:
    print('[lpa] SIGUSR1 received – showing window.')
    window.show_window()
    return GLib.SOURCE_CONTINUE


def on_quit(
    app: Gio.Application,
    state: State,
    lofi_player: LoFiPlayer,
    ambience_player: AmbiencePlayer,
    tray=None,
) -> None:
    print('[lpa] Shutting down …')

    try:
        lofi_player.stop()
        lofi_player.cleanup()
    except Exception as exc:
        print(f'[lpa] Warning: error stopping LoFi player: {exc}')

    try:
        ambience_player.stop_all()
        ambience_player.cleanup()
    except Exception as exc:
        print(f'[lpa] Warning: error stopping Ambience player: {exc}')

    try:
        state.save()
    except Exception as exc:
        print(f'[lpa] Warning: could not save state: {exc}')

    if tray is not None:
        try:
            tray.shutdown()
        except Exception as exc:
            print(f'[lpa] Warning: error shutting down tray: {exc}')

    _remove_pid_file()

    app.quit()

def on_activate(
    app: Gio.Application,
    *_args,
) -> None:
    state = State.load()

    lofi_player = LoFiPlayer()
    ambience_player = AmbiencePlayer()
    window = MainWindow(
        app,
        state,
        lofi_player,
        ambience_player,
        APP_DIR,
    )

    tray = TrayIcon(
        APP_DIR,
        window.show_window,
        lambda: on_quit(app, state, lofi_player, ambience_player, tray),
    )

    try:
        from audio.mpris import LPMprisServer
        window._mpris_server = LPMprisServer(lofi_player, ambience_player, window.lofi_tab) #vulture: ignore
    except Exception as exc:
        print(f'[lpa] Warning: Failed to initialise MPRIS server: {exc}')


    try:
        gi.require_version('GLibUnix', '2.0')
        from gi.repository import GLibUnix
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, _on_sigusr1, window)
    except (ImportError, AttributeError):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, _on_sigusr1, window)
    window.present()


def main() -> int:
    _enforce_single_instance()
    if Notify is not None:
        try:
            Notify.init('lpa')
        except Exception as exc:
            print(f'[lpa] Warning: Notify.init failed: {exc}')
    app = Gtk.Application(
        application_id='io.github.mareomanoj6.lpa',
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )

    app.connect('activate', on_activate)
    def _sigint_handler(sig, frame):
        print('\n[lpa] Interrupted. Exiting cleanly.')
        app.quit()

    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        return app.run(sys.argv)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    sys.exit(main())
