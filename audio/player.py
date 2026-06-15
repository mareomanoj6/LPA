import os
import subprocess
import threading
from typing import Callable
from urllib.parse import urlparse
import pathlib


import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)


def _to_uri(path_or_url: str) -> str:
    parsed = urlparse(path_or_url)
    if parsed.scheme in ('http', 'https', 'file'):
        return path_or_url
    return pathlib.Path(path_or_url).absolute().as_uri()


class LoFiPlayer:

    def __init__(self):
        self._player = Gst.ElementFactory.make("playbin", "lofi_player")
        if not self._player:
            print("[LoFiPlayer] Failed to create GStreamer playbin.")
        else:
            self._player.set_property("flags", 2)
            
            bus = self._player.get_bus()
            bus.add_signal_watch()
            bus.connect("message::error", self._on_error)
            bus.connect("message::eos", self._on_eos)
            
        self.on_status: Callable[[str], None] | None = None
        self.on_state_changed: Callable[[], None] | None = None
        self._last_mrl = None
        self._current_track_name = "Lo-Fi Stream"
        self._reconnect_attempts = 0
        self._reconnect_source = None

    def _on_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"[LoFiPlayer] GStreamer error: {err.message}", flush=True)
        self._schedule_reconnect()

    def _on_eos(self, bus, msg):
        print("[LoFiPlayer] GStreamer EOS reached.", flush=True)
        self._schedule_reconnect()

    def _schedule_reconnect(self):
        if not self._last_mrl:
            return
        
        self._reconnect_attempts += 1
        delay_s = min(30, 2 ** self._reconnect_attempts)
        print(f"[LoFiPlayer] Reconnecting in {delay_s}s...", flush=True)
        
        if self.on_status:
            GLib.idle_add(self.on_status, f"Reconnecting in {delay_s}s...")
            
        if self._reconnect_source is not None:
            GLib.source_remove(self._reconnect_source)
            
        self._reconnect_source = GLib.timeout_add(delay_s * 1000, self._do_reconnect)

    def _do_reconnect(self):
        self._reconnect_source = None
        if self._last_mrl:
            if self.on_status:
                self.on_status("Reconnecting...")
            self._play_media(self._last_mrl, is_reconnect=True)
        return False

    def _play_media(self, mrl: str, is_reconnect: bool = False) -> None:
        if not self._player:
            return

        if not is_reconnect:
            self._reconnect_attempts = 0
            self._last_mrl = mrl
            if self._reconnect_source is not None:
                GLib.source_remove(self._reconnect_source)
                self._reconnect_source = None

        self.stop()
        uri = _to_uri(mrl)
        self._player.set_property("uri", uri)
        self._player.set_state(Gst.State.PLAYING)
        if self.on_state_changed:
            GLib.idle_add(self.on_state_changed)
        
        if is_reconnect and self.on_status:
            GLib.idle_add(self.on_status, "Playing")

    def play_url(self, url: str) -> None:
        self._play_media(url)

    def play_youtube(
        self,
        youtube_url: str,
        callback: Callable[[bool, str | None], None] | None = None,
    ) -> None:

        def _fire_callback(success: bool, err: str | None = None) -> None:
            if callback:
                GLib.idle_add(callback, success, err)

        def _run_ytdlp(extra_args: list[str] = []) -> subprocess.CompletedProcess | None:
            try:
                ytdlp_bin = "/app/bin/yt-dlp"
                if not os.path.exists(ytdlp_bin):
                    import shutil
                    ytdlp_bin = shutil.which("yt-dlp") or "yt-dlp"

                return subprocess.run(
                    [
                        ytdlp_bin,
                        "--format", "bestaudio/best",
                        "--get-url",
                        "--no-playlist",
                        "--quiet",
                        *extra_args,
                        youtube_url,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except FileNotFoundError:
                return None
            except subprocess.TimeoutExpired:
                raise

        def _extract_and_play() -> None:
            try:
                ytdlp_bin = "/app/bin/yt-dlp"
                if not os.path.exists(ytdlp_bin):
                    import shutil
                    ytdlp_bin = shutil.which("yt-dlp") or "yt-dlp"

                if ytdlp_bin == "yt-dlp" and not __import__('shutil').which("yt-dlp"):
                    _fire_callback(False, "yt-dlp not found. Please install it.")
                    return

                result = _run_ytdlp()
                if result is None:
                    _fire_callback(False, "yt-dlp not found. Please install it.")
                    return

                audio_url = result.stdout.strip().splitlines()[0] if result.returncode == 0 else ""

                if result.returncode != 0 or not audio_url:
                    first_err = result.stderr.strip() if result else ""
                    print(f"[LoFiPlayer] yt-dlp error (attempt 1): {first_err}")
                    print("[LoFiPlayer] Retrying with --live-from-start for live streams…")
                    result2 = _run_ytdlp(["--live-from-start"])
                    if result2 and result2.returncode == 0:
                        audio_url = result2.stdout.strip().splitlines()[0] if result2.stdout.strip() else ""
                    if not audio_url:
                        err = first_err or (result2.stderr.strip() if result2 else "yt-dlp returned non-zero exit code")
                        print(f"[LoFiPlayer] yt-dlp error (attempt 2): {err}")
                        _fire_callback(False, err)
                        return

                GLib.idle_add(self._play_media, audio_url)
                _fire_callback(True, None)

            except subprocess.TimeoutExpired:
                err = "yt-dlp timed out after 60 seconds."
                print(f"[LoFiPlayer] {err}")
                _fire_callback(False, err)
            except Exception as exc:
                err = str(exc)
                print(f"[LoFiPlayer] Unexpected error during yt-dlp extraction: {err}")
                _fire_callback(False, err)

        thread = threading.Thread(target=_extract_and_play, daemon=True, name="yt-dlp-extract")
        thread.start()

    def play_file(self, path: str) -> None:
        self._play_media(path)

    def stop(self) -> None:
        if self._reconnect_source is not None:
            GLib.source_remove(self._reconnect_source)
            self._reconnect_source = None
        self._last_mrl = None
        self._reconnect_attempts = 0
            
        if self._player:
            self._player.set_state(Gst.State.READY)
            if self.on_state_changed:
                GLib.idle_add(self.on_state_changed)

    def pause_resume(self) -> None:
        if not self._player:
            return
        _, state, _ = self._player.get_state(0)
        if state == Gst.State.PLAYING:
            self._player.set_state(Gst.State.PAUSED)
            if self.on_state_changed:
                GLib.idle_add(self.on_state_changed)
        elif state == Gst.State.PAUSED:
            self._player.set_state(Gst.State.PLAYING)
            if self.on_state_changed:
                GLib.idle_add(self.on_state_changed)


    def is_playing(self) -> bool:
        if not self._player:
            return False
        _, state, _ = self._player.get_state(0)
        return state == Gst.State.PLAYING

    def set_volume(self, vol: int) -> None:
        if not self._player:
            return
        vol = max(0, min(100, int(vol)))
        self._player.set_property("volume", vol / 100.0)

    def get_volume(self) -> int:
        if not self._player:
            return 0
        vol = self._player.get_property("volume")
        return int(vol * 100)

    def get_elapsed_seconds(self) -> int:
        if not self._player:
            return 0
        success, pos = self._player.query_position(Gst.Format.TIME)
        if success:
            return pos // Gst.SECOND
        return 0


    def get_state(self) -> str:
        if not self._player:
            return "stopped"
        _, state, _ = self._player.get_state(0)
        if state == Gst.State.PLAYING:
            return "playing"
        if state == Gst.State.PAUSED:
            return "paused"
        return "stopped"

    def cleanup(self) -> None:
        self.stop()
        if self._player:
            self._player.set_state(Gst.State.NULL)
            self._player = None

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass


class AmbiencePlayer:

    def __init__(self):
        self._players: dict[str, Gst.Element] = {}
        self._volumes: dict[str, float] = {}
        self.on_state_changed: Callable[[], None] | None = None

    def _get_or_create_player(self, sound_id: str) -> Gst.Element:
        if sound_id not in self._players:
            player = Gst.ElementFactory.make("playbin", f"ambience_{sound_id}")
            if not player:
                print(f"[AmbiencePlayer] Failed to create playbin for {sound_id}")
                return None
            
            player.set_property("flags", 2)
        
            bus = player.get_bus()
            bus.add_signal_watch()
            bus.connect("message::eos", self._on_eos, player)
            
            self._players[sound_id] = player
            self._volumes[sound_id] = 1.0
        return self._players[sound_id]

    def _on_eos(self, bus, msg, player):
        player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        return True

    def play(self, sound_id: str, file_path: str) -> None:
        player = self._get_or_create_player(sound_id)
        if not player:
            return

        self.stop(sound_id)
        
        uri = _to_uri(file_path)
        player.set_property("uri", uri)
        
        vol = self._volumes.get(sound_id, 1.0)
        player.set_property("volume", vol)
        
        player.set_state(Gst.State.PLAYING)
        if self.on_state_changed:
            GLib.idle_add(self.on_state_changed)

    def stop(self, sound_id: str) -> None:
        player = self._players.get(sound_id)
        if player:
            player.set_state(Gst.State.READY)
            if self.on_state_changed:
                GLib.idle_add(self.on_state_changed)

    def stop_all(self) -> None:
        changed = False
        for sound_id in list(self._players.keys()):
            player = self._players.get(sound_id)
            if player:
                player.set_state(Gst.State.READY)
                changed = True
        if changed and self.on_state_changed:
            GLib.idle_add(self.on_state_changed)

    def set_volume(self, sound_id: str, vol: int) -> None:
        vol = max(0, min(100, int(vol)))
        vol_float = vol / 100.0
        self._volumes[sound_id] = vol_float
        
        player = self._players.get(sound_id)
        if player:
            player.set_property("volume", vol_float)

    def get_volume(self, sound_id: str) -> int:
        if sound_id in self._volumes:
            return int(self._volumes[sound_id] * 100)
        player = self._players.get(sound_id)
        if player:
            vol = player.get_property("volume")
            return int(vol * 100)
        return 0

    def is_playing(self, sound_id: str) -> bool:
        player = self._players.get(sound_id)
        if not player:
            return False
        _, state, _ = player.get_state(0)
        return state == Gst.State.PLAYING

    def is_any_playing(self) -> bool:
        for sound_id in self._players:
            if self.is_playing(sound_id):
                return True
        return False

    def cleanup(self) -> None:
        self.stop_all()
        for player in self._players.values():
            try:
                bus = player.get_bus()
                if bus:
                    bus.remove_signal_watch()
                player.set_state(Gst.State.NULL)
            except Exception:
                pass
        self._players.clear()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
