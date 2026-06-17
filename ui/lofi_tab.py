import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib



def _fmt_elapsed(seconds: int) -> str:
    h  = seconds // 3600
    m  = (seconds % 3600) // 60
    s  = seconds % 60
    return f'{h:02d}:{m:02d}:{s:02d}'

class LoFiTab(Gtk.Box):
    def __init__(self, state, player):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.state  = state
        self.player = player

        self._now_playing: dict | None = None
        self._elapsed_source: int | None = None


        self._build_ui()
        vol = getattr(self.state, 'lofi_volume', 70)
        self.vol_slider.set_value(vol)
        
        self.player.on_status = self._on_player_status

    def set_active(self, active: bool):
        if not active:
            self._stop_elapsed_ticker()
        else:
            if self.player.is_playing() and self._now_playing is not None:
                self._start_elapsed_ticker()

    def _on_player_status(self, status: str):
        self.lbl_elapsed.set_label(status)

    def _build_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_vbox.set_halign(Gtk.Align.CENTER)
        main_vbox.set_valign(Gtk.Align.CENTER)
        main_vbox.set_vexpand(True)
        
        # Title
        title = Gtk.Label(label="lo-fi")
        title.add_css_class("title-medium")
        main_vbox.append(title)
        
        # Center Row (Volume, Graphic, Controls)
        center_hbox = Gtk.CenterBox()
        center_hbox.set_halign(Gtk.Align.CENTER)
        
        # Volume Slider (Vertical)
        self.vol_slider = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
        self.vol_slider.set_inverted(True)
        self.vol_slider.set_size_request(-1, 100)
        self.vol_slider.set_draw_value(False)
        self.vol_slider.add_css_class("vol-slider")
        self.vol_slider.set_margin_start(20)
        self.vol_slider.connect('value-changed', self._on_volume_changed)
        
        slider_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        slider_wrapper.set_halign(Gtk.Align.CENTER)
        slider_wrapper.append(self.vol_slider)
        center_hbox.set_start_widget(slider_wrapper)
        
        # Concentric Circles Graphic
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.drawing_area.set_size_request(160, 160)
        self.drawing_area.set_margin_start(16)
        self.drawing_area.set_margin_end(16)
        self.drawing_area.set_draw_func(self._draw_graphic, None)
        center_hbox.set_center_widget(self.drawing_area)
        
        # Controls (Play/Pause, Stop)
        controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        controls_vbox.set_valign(Gtk.Align.CENTER)
        controls_vbox.set_halign(Gtk.Align.CENTER)
        
        self.btn_play_pause = Gtk.Button()
        self.btn_play_pause.set_icon_name("media-playback-start-symbolic")
        self.btn_play_pause.add_css_class("flat")
        self.btn_play_pause.connect("clicked", self._on_play_pause_bar)
        controls_vbox.append(self.btn_play_pause)
        
        self.btn_stop = Gtk.Button()
        self.btn_stop.set_icon_name("media-playback-stop-symbolic")
        self.btn_stop.add_css_class("flat")
        self.btn_stop.connect("clicked", self._on_stop)
        controls_vbox.append(self.btn_stop)
        
        center_hbox.set_end_widget(controls_vbox)
        main_vbox.append(center_hbox)
        
        # Stream info
        self.lbl_now_playing = Gtk.Label(label="no streams playing...")
        self.lbl_now_playing.add_css_class("title-medium")
        main_vbox.append(self.lbl_now_playing)
        
        self.lbl_elapsed = Gtk.Label(label="")
        self.lbl_elapsed.add_css_class("muted")
        main_vbox.append(self.lbl_elapsed)
        
        # Stream MenuButton (replacing DropDown)
        self.stream_btn = Gtk.MenuButton()
        self.stream_btn.set_label("--- Select a stream ---")
        self.stream_btn.set_always_show_arrow(True)
        
        self.stream_popover = Gtk.Popover()
        self.stream_btn.set_popover(self.stream_popover)
        
        self.stream_listbox = Gtk.ListBox()
        self.stream_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.stream_listbox.connect("row-activated", self._on_stream_menu_row_activated)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        scroll.set_max_content_height(250)
        scroll.set_child(self.stream_listbox)
        self.stream_popover.set_child(scroll)
        
        main_vbox.append(self.stream_btn)
        
        self.append(main_vbox)
        self._refresh_streams()

    def _draw_graphic(self, area, cr, width, height, _data):
        import math
        cx = width / 2.0
        cy = height / 2.0
        
        cr.set_source_rgb(1.0, 1.0, 1.0) 
        
        max_r = min(cx, cy) - max(16, int(min(cx, cy) * 0.1))
        cr.set_line_width(max(2, int(max_r * 0.05)))
        
        radii = [max_r * 0.3, max_r * 0.6, max_r * 0.9]
        for r in radii:
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()
            
    def _refresh_streams(self):
        self._all_stations = list(getattr(self.state, 'custom_streams', []) or [])
        
        while self.stream_listbox.get_first_child() is not None:
            self.stream_listbox.remove(self.stream_listbox.get_first_child())
            
        for idx, station in enumerate(self._all_stations):
            lbl = Gtk.Label(label=station['name'])
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_start(12)
            lbl.set_margin_end(12)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            row = Gtk.ListBoxRow()
            row.set_child(lbl)
            row._stream_idx = idx
            self.stream_listbox.append(row)
            
        if self._now_playing is None:
            self.stream_btn.set_label("--- Select a stream ---")

    def _on_stream_menu_row_activated(self, _listbox, row):
        idx = row._stream_idx
        self.stream_popover.popdown()
        if idx >= 0 and idx < len(self._all_stations):
            station = self._all_stations[idx]
            self.stream_btn.set_label(station['name'])
            self._on_play_station(station)

    
    def _on_play_station(self, station: dict):
        if self._now_playing is not None and self._now_playing.get('name') == station['name']:
            self._stop_playback()
            return

        if self._now_playing is not None:
            try:
                self.player.stop()
            except Exception:
                pass

        stype = station.get('type', 'radio')
        btn_play = self.btn_play_pause

        if stype == 'youtube':

            self.lbl_now_playing.set_label(f'Loading {station["name"]}…')
            self.lbl_elapsed.set_label('')

            def _on_yt_ready(success: bool, error_msg: str = ''):

                if success:
                    self._activate_station(station, btn_play)
                else:
                    self.lbl_now_playing.set_label('Failed to load stream')

            try:
                self.player.play_youtube(station['url'], _on_yt_ready)
            except Exception as exc:
                _on_yt_ready(False, str(exc))

        elif stype == 'local':
            try:
                self.player.play_file(station['url'])
                self._activate_station(station, btn_play)
            except Exception as exc:
                pass

        else:
            try:
                self.player.play_url(station['url'])
                self._activate_station(station, btn_play)
            except Exception as exc:
                pass

    def _activate_station(self, station: dict, btn_play: Gtk.Button):
        self._now_playing        = station
        self.player._current_track_name = station['name']

        try:
            self.player.set_volume(int(self.vol_slider.get_value()))
        except Exception:
            pass

        self.lbl_now_playing.set_label(station['name'])
        self.stream_btn.set_label(station['name'])
        self.lbl_elapsed.set_label(_fmt_elapsed(0))
        self.btn_play_pause.set_icon_name('media-playback-pause-symbolic')

        self._start_elapsed_ticker()

    def _on_play_pause_bar(self, _btn):
        if self._now_playing is None:
            return
        try:
            self.player.pause_resume()
            if self.player.is_playing():
                self.btn_play_pause.set_icon_name('media-playback-pause-symbolic')
                self._start_elapsed_ticker()
            else:
                self.btn_play_pause.set_icon_name('media-playback-start-symbolic')
                self._stop_elapsed_ticker()
        except Exception:
            pass

    def _on_stop(self, _btn):
        self._stop_playback()

    def _stop_playback(self):
        self._stop_elapsed_ticker()
        try:
            self.player.stop()
        except Exception:
            pass
        self._now_playing = None
        self.lbl_now_playing.set_label('Nothing playing')
        self.stream_btn.set_label('--- Select a stream ---')
        self.lbl_elapsed.set_label('')
        self.btn_play_pause.set_icon_name('media-playback-start-symbolic')

    def play_next(self):
        if not self._all_stations or len(self._all_stations) <= 1:
            return
        if self._now_playing is None:
            idx = 0
        else:
            try:
                idx = self._all_stations.index(self._now_playing)
            except ValueError:
                idx = 0
            idx = (idx + 1) % len(self._all_stations)
        st = self._all_stations[idx]
        self._on_play_station(st)

    def play_previous(self):
        if not self._all_stations or len(self._all_stations) <= 1:
            return
        if self._now_playing is None:
            idx = len(self._all_stations) - 1
        else:
            try:
                idx = self._all_stations.index(self._now_playing)
            except ValueError:
                idx = 0
            idx = (idx - 1) % len(self._all_stations)
        st = self._all_stations[idx]
        self._on_play_station(st)

    def _on_volume_changed(self, scale):
        vol = int(scale.get_value())
        self.state.lofi_volume = vol
        try:
            self.state.save_debounced()
        except Exception:
            pass
        try:
            self.player.set_volume(vol)
        except Exception:
            pass

    def _start_elapsed_ticker(self):
        self._stop_elapsed_ticker()
        self._elapsed_source = GLib.timeout_add(1000, self._update_elapsed)

    def _stop_elapsed_ticker(self):
        if self._elapsed_source is not None:
            GLib.source_remove(self._elapsed_source)
            self._elapsed_source = None

    def _update_elapsed(self) -> bool:
        if self._now_playing is None:
            self._elapsed_source = None
            return GLib.SOURCE_REMOVE
        try:
            secs = self.player.get_elapsed_seconds()
            self.lbl_elapsed.set_label(_fmt_elapsed(secs))
        except Exception:
            pass
        return GLib.SOURCE_CONTINUE

