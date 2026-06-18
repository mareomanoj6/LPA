import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib

MPRIS_XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"></method>
    <method name="Quit"></method>
    <property name="CanQuit" type="b" access="read"/>
    <property name="Fullscreen" type="b" access="readwrite"/>
    <property name="CanSetFullscreen" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"></method>
    <method name="Previous"></method>
    <method name="Pause"></method>
    <method name="PlayPause"></method>
    <method name="Stop"></method>
    <method name="Play"></method>
    <method name="Seek">
      <arg direction="in" name="Offset" type="x"/>
    </method>
    <method name="SetPosition">
      <arg direction="in" name="TrackId" type="o"/>
      <arg direction="in" name="Position" type="x"/>
    </method>
    <method name="OpenUri">
      <arg direction="in" name="Uri" type="s"/>
    </method>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""

class LPMprisServer:
    def __init__(self, lofi_player, ambience_player, lofi_tab):
        self.lofi_player = lofi_player
        self.ambience_player = ambience_player
        self.lofi_tab = lofi_tab

        self.lofi_player.on_state_changed = self._on_state_changed
        self.ambience_player.on_state_changed = self._on_state_changed

        self.node_info = Gio.DBusNodeInfo.new_for_xml(MPRIS_XML)
        self.connection = None
        self.reg_id1 = 0
        self.reg_id2 = 0
        self._name_id = 0

        self.connect()

    def connect(self):
        Gio.bus_get(Gio.BusType.SESSION, None, self._on_bus_get)

    def _on_bus_get(self, source_object, res):
        try:
            self.connection = Gio.bus_get_finish(res)
            
            self.reg_id1 = self.connection.register_object(
                "/org/mpris/MediaPlayer2",
                self.node_info.interfaces[0],
                self._handle_method_call,
                self._handle_get_property,
                self._handle_set_property
            )
            self.reg_id2 = self.connection.register_object(
                "/org/mpris/MediaPlayer2",
                self.node_info.interfaces[1],
                self._handle_method_call,
                self._handle_get_property,
                self._handle_set_property
            )
            
            self._name_id = Gio.bus_own_name_on_connection(
                self.connection,
                "org.mpris.MediaPlayer2.io.github.mareomanoj6.lpa",
                Gio.BusNameOwnerFlags.NONE,
                None, None
            )
        except Exception as e:
            print(f"[MPRIS] Failed to register: {e}")

    def _get_playback_status(self):
        if self.lofi_player.is_playing() or self.ambience_player.is_any_playing():
            return "Playing"
        if self.lofi_player.get_state() == "paused":
            return "Paused"
        return "Stopped"

    def _get_metadata(self):
        title = ""
        if self.lofi_player.is_playing() or self.lofi_player.get_state() == "paused":
            title = self.lofi_player._current_track_name
        elif self.ambience_player.is_any_playing():
            title = "Ambience"
        else:
            title = "LPA"
        
        return {
            "mpris:trackid": GLib.Variant("s", "/org/mpris/MediaPlayer2/TrackList/NoTrack"),
            "xesam:title": GLib.Variant("s", title),
            "mpris:artUrl": GLib.Variant("s", "file:///app/share/icons/hicolor/256x256/apps/io.github.mareomanoj6.lpa.png")
        }

    def _handle_method_call(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        if interface_name == "org.mpris.MediaPlayer2.Player":
            if method_name == "PlayPause":
                self.lofi_player.pause_resume()
            elif method_name == "Pause":
                if self.lofi_player.is_playing():
                    self.lofi_player.pause_resume()
            elif method_name == "Play":
                if not self.lofi_player.is_playing():
                    self.lofi_player.pause_resume()
            elif method_name == "Stop":
                self.lofi_player.stop()
                self.ambience_player.stop_all()
            elif method_name == "Next":
                if self.lofi_tab:
                    GLib.idle_add(self.lofi_tab.play_next)
            elif method_name == "Previous":
                if self.lofi_tab:
                    GLib.idle_add(self.lofi_tab.play_previous)

        invocation.return_value(None)

    def _handle_get_property(self, connection, sender, object_path, interface_name, property_name):
        if interface_name == "org.mpris.MediaPlayer2":
            if property_name == "CanQuit":
                return GLib.Variant("b", False)
            elif property_name == "Fullscreen":
                return GLib.Variant("b", False)
            elif property_name == "CanSetFullscreen":
                return GLib.Variant("b", False)
            elif property_name == "CanRaise":
                return GLib.Variant("b", False)
            elif property_name == "HasTrackList":
                return GLib.Variant("b", False)
            elif property_name == "Identity":
                return GLib.Variant("s", "LPA")
            elif property_name == "DesktopEntry":
                return GLib.Variant("s", "io.github.mareomanoj6.lpa")
            elif property_name == "SupportedUriSchemes":
                return GLib.Variant("as", [])
            elif property_name == "SupportedMimeTypes":
                return GLib.Variant("as", [])

        elif interface_name == "org.mpris.MediaPlayer2.Player":
            if property_name == "PlaybackStatus":
                return GLib.Variant("s", self._get_playback_status())
            elif property_name == "LoopStatus":
                return GLib.Variant("s", "None")
            elif property_name == "Rate":
                return GLib.Variant("d", 1.0)
            elif property_name == "Shuffle":
                return GLib.Variant("b", False)
            elif property_name == "Metadata":
                return GLib.Variant("a{sv}", self._get_metadata())
            elif property_name == "Volume":
                return GLib.Variant("d", self.lofi_player.get_volume() / 100.0)
            elif property_name == "Position":
                return GLib.Variant("x", self.lofi_player.get_elapsed_seconds() * 1000000)
            elif property_name == "MinimumRate":
                return GLib.Variant("d", 1.0)
            elif property_name == "MaximumRate":
                return GLib.Variant("d", 1.0)
            elif property_name == "CanGoNext":
                return GLib.Variant("b", True)
            elif property_name == "CanGoPrevious":
                return GLib.Variant("b", True)
            elif property_name == "CanPlay":
                return GLib.Variant("b", True)
            elif property_name == "CanPause":
                return GLib.Variant("b", True)
            elif property_name == "CanSeek":
                return GLib.Variant("b", False)
            elif property_name == "CanControl":
                return GLib.Variant("b", True)

        return None

    def _handle_set_property(self, connection, sender, object_path, interface_name, property_name, value):
        return True

    def _on_state_changed(self):
        if not self.connection:
            return
            
        changed_props = {
            "PlaybackStatus": GLib.Variant("s", self._get_playback_status()),
            "Metadata": GLib.Variant("a{sv}", self._get_metadata())
        }
            
        self.connection.emit_signal(
            None,
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant("(sa{sv}as)", ("org.mpris.MediaPlayer2.Player", changed_props, []))
        )
