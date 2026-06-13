import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

import math
import os
import datetime


SURFACE = '#161b22'
BORDER  = '#30363d'
TEXT    = '#e6edf3'
MUTED   = '#8b949e'
GREEN   = '#22c55e'
AMBER   = '#f59e0b'
BLUE    = '#3b82f6'


PHASE_COLORS = {
    'work':        GREEN,
    'short_break': AMBER,
}

PHASE_LABELS = {
    'work':        'WORK',
    'short_break': 'SHORT BREAK',
}

def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _apply_css(widget, css: str):
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    widget.get_style_context().add_provider(
        provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

class PomodoroTab(Gtk.Box):
    def __init__(self, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.state = state

        self.phase         = 'work'
        self.session_count = 0     
        self.is_running    = False
        self._tick_source  = None 
        self._bg_source    = None
        self._is_active    = True

        self._reset_timer_values()

        self._phase_start_dt: datetime.datetime | None = None

        self._build_top_section()
        self._build_bottom_section()

    def set_active(self, active: bool):
        self._is_active = active
        if not active:
            if self._tick_source is not None:
                GLib.source_remove(self._tick_source)
                self._tick_source = None
            if self.is_running and self.remaining_seconds > 0:
                self._bg_source = GLib.timeout_add(self.remaining_seconds * 1000, self._on_bg_timeout)
        else:
            if self._bg_source is not None:
                GLib.source_remove(self._bg_source)
                self._bg_source = None
            if self.is_running:
                if self._phase_start_dt is not None:
                    elapsed = (datetime.datetime.now() - self._phase_start_dt).total_seconds()
                    self.remaining_seconds = max(0, int(self.total_seconds - elapsed))
                    if self.remaining_seconds > 0:
                        self._tick_source = GLib.timeout_add(1000, self._tick)
                    else:
                        self._on_phase_complete()
                self.drawing_area.queue_draw()

    def _on_bg_timeout(self) -> bool:
        self._bg_source = None
        self.remaining_seconds = 0
        self._on_phase_complete()
        return GLib.SOURCE_REMOVE


    def _seconds_for_phase(self, phase: str) -> int:
        mapping = {
            'work':        self.state.work_duration * 60,
            'short_break': self.state.short_break   * 60,
        }
        return mapping[phase]

    def _reset_timer_values(self):
        self.total_seconds     = self._seconds_for_phase(self.phase)
        self.remaining_seconds = self.total_seconds


    def _build_top_section(self):
        # We will build a unified dashboard card
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_vbox.set_halign(Gtk.Align.CENTER)
        main_vbox.set_valign(Gtk.Align.CENTER)
        main_vbox.set_vexpand(True)
        
        # Title
        title = Gtk.Label(label="pomodoro")
        title.add_css_class("title-medium")
        title.set_margin_bottom(10)
        main_vbox.append(title)
        
        # Center row with ring and controls
        center_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        center_hbox.set_halign(Gtk.Align.CENTER)
        
        # Play/Pause button
        self.btn_start_pause = Gtk.Button()
        self.btn_start_pause.set_icon_name("media-playback-start-symbolic")
        self.btn_start_pause.add_css_class("flat")
        self.btn_start_pause.connect("clicked", self._on_start_pause)
        center_hbox.append(self.btn_start_pause)
        
        # Ring drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.drawing_area.set_size_request(160, 160)
        self.drawing_area.set_draw_func(self._draw_ring, None)
        center_hbox.append(self.drawing_area)
        
        # Stop button
        btn_stop = Gtk.Button()
        btn_stop.set_icon_name("media-playback-stop-symbolic")
        btn_stop.add_css_class("flat")
        btn_stop.connect("clicked", self._on_reset)
        center_hbox.append(btn_stop)
        
        main_vbox.append(center_hbox)
        
        # Bottom controls (W, B, S)
        bottom_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        bottom_hbox.set_halign(Gtk.Align.CENTER)
        
        self.work_entry = self._create_editable_stat("W", self.state.work_duration, self._on_work_changed, 5, 120)
        bottom_hbox.append(self.work_entry)
        
        self.break_entry = self._create_editable_stat("B", self.state.short_break, self._on_short_changed, 5, 60)
        bottom_hbox.append(self.break_entry)
        
        main_vbox.append(bottom_hbox)
        
        main_vbox.set_margin_bottom(20)
        
        self.append(main_vbox)

    def _create_editable_stat(self, label_text, default_val, callback, min_val, max_val):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_halign(Gtk.Align.CENTER)
        
        entry = Gtk.Entry()
        entry.set_text(str(default_val))
        entry.set_width_chars(3)
        entry.set_alignment(0.5)
        entry.add_css_class("stat-entry")
        
        entry._debounce_id = 0
        def on_changed(*args):
            try:
                text = entry.get_text()
                if not text:
                    return
                val = int(text)
                
                # Immediately clamp maximum visually
                if val > max_val:
                    entry.set_text(str(max_val))
                    entry.set_position(-1)
                    val = max_val
                
                # Update underlying timer state immediately, clamping minimum
                clamped = max(min_val, val)
                callback(clamped)
                
                # Wait 1.5s after typing stops to visually clamp minimum
                if entry._debounce_id:
                    GLib.source_remove(entry._debounce_id)
                def snap_visual():
                    entry._debounce_id = 0
                    try:
                        current_val = int(entry.get_text())
                        c = max(min_val, min(max_val, current_val))
                        if current_val != c:
                            entry.set_text(str(c))
                            entry.set_position(-1)
                    except ValueError:
                        entry.set_text(str(min_val))
                    return False
                entry._debounce_id = GLib.timeout_add(1500, snap_visual)
                
            except ValueError:
                pass

        entry.connect("changed", on_changed)
        
        def commit_val(*args):
            if entry._debounce_id:
                GLib.source_remove(entry._debounce_id)
                entry._debounce_id = 0
            try:
                val = int(entry.get_text())
                clamped = max(min_val, min(max_val, val))
                if val != clamped:
                    entry.set_text(str(clamped))
                    entry.set_position(-1)
                callback(clamped)
            except ValueError:
                entry.set_text(str(min_val))
                callback(min_val)

        entry.connect("activate", commit_val)
        
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("leave", commit_val)
        entry.add_controller(focus_ctrl)
        
        vbox.append(entry)
        
        lbl = Gtk.Label(label=label_text)
        lbl.add_css_class("muted")
        vbox.append(lbl)
        
        return vbox

    def _build_bottom_section(self):
        pass # Remove log list from dashboard

    def _draw_ring(self, area, cr, width, height, _data):
        cx = width  / 2.0
        cy = height / 2.0
        radius      = min(cx, cy) - max(16, int(min(cx, cy) * 0.1))
        stroke_width = max(4, int(radius * 0.22))

        if self.total_seconds > 0:
            elapsed  = self.total_seconds - self.remaining_seconds
            progress = elapsed / self.total_seconds
        else:
            progress = 0.0

        r, g, b = _hex_to_rgb(BORDER)
        cr.set_source_rgb(r, g, b)
        cr.set_line_width(stroke_width)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        if progress > 0.0:
            phase_hex   = PHASE_COLORS.get(self.phase, GREEN)
            r, g, b     = _hex_to_rgb(phase_hex)
            cr.set_source_rgb(r, g, b)
            cr.set_line_width(stroke_width)
            cr.set_line_cap(1)

            start_angle = -math.pi / 2
            end_angle   = start_angle + 2 * math.pi * progress
            cr.arc(cx, cy, radius, start_angle, end_angle)
            cr.stroke()

        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds  % 60
        time_str = f'{mins:02d}:{secs:02d}'

        cr.set_source_rgb(*_hex_to_rgb(TEXT))
        import gi
        gi.require_version('Pango', '1.0')
        gi.require_version('PangoCairo', '1.0')
        from gi.repository import Pango as _Pango, PangoCairo

        layout = PangoCairo.create_layout(cr)
        font_size = max(12, int(radius * 0.35))
        desc   = _Pango.FontDescription.from_string(f'JetBrains Mono Bold {font_size}')
        layout.set_font_description(desc)
        layout.set_text(time_str, -1)
        lw, lh = layout.get_pixel_size()
        cr.move_to(cx - lw / 2, cy - lh / 2 - 8)
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgb(*_hex_to_rgb(MUTED))
        sub_layout = PangoCairo.create_layout(cr)
        sub_font_size = max(8, int(radius * 0.12))
        sub_desc   = _Pango.FontDescription.from_string(f'JetBrains Mono {sub_font_size}')
        sub_layout.set_font_description(sub_desc)
        sub_layout.set_text(PHASE_LABELS.get(self.phase, ''), -1)
        sw, _ = sub_layout.get_pixel_size()
        cr.move_to(cx - sw / 2, cy + lh / 2 - 2)
        PangoCairo.show_layout(cr, sub_layout)


    def _on_start_pause(self, _btn):
        if self.is_running:
            self._pause_timer()
        else:
            self._start_timer()

    def _start_timer(self):
        if self._phase_start_dt is None:
            self._phase_start_dt = datetime.datetime.now()

        self.is_running = True
        self.btn_start_pause.set_icon_name('media-playback-pause-symbolic')
        
        if not self._is_active:
            if self._bg_source is None:
                self._bg_source = GLib.timeout_add(self.remaining_seconds * 1000, self._on_bg_timeout)
        else:
            if self._tick_source is None:
                self._tick_source = GLib.timeout_add(1000, self._tick)

    def _pause_timer(self):
        self.is_running = False
        self.btn_start_pause.set_icon_name('media-playback-start-symbolic')
        if self._tick_source is not None:
            GLib.source_remove(self._tick_source)
            self._tick_source = None
        if self._bg_source is not None:
            GLib.source_remove(self._bg_source)
            self._bg_source = None

    def _on_reset(self, _btn):
        self._stop_ticker()
        self.is_running        = False
        self.session_count     = 0
        self.phase             = 'work'
        self._phase_start_dt   = None
        self._reset_timer_values()
        self.btn_start_pause.set_icon_name('media-playback-start-symbolic')
        self.drawing_area.queue_draw()


    def _stop_ticker(self):
        if self._tick_source is not None:
            GLib.source_remove(self._tick_source)
            self._tick_source = None
        if self._bg_source is not None:
            GLib.source_remove(self._bg_source)
            self._bg_source = None

    def _tick(self) -> bool:
        if not self.is_running:
            self._tick_source = None
            return GLib.SOURCE_REMOVE

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.drawing_area.queue_draw()
            return GLib.SOURCE_CONTINUE

        self._tick_source = None
        self._on_phase_complete()
        return GLib.SOURCE_REMOVE

    def _on_phase_complete(self):
        self.is_running = False
        self._play_chime()
        self._send_notification()

        if self.phase == 'work':
            self.session_count += 1

        self._phase_start_dt = None
        self._show_phase_end_dialog()

    def _show_phase_end_dialog(self):
        dialog = Gtk.Dialog()
        dialog.set_title('Phase Complete')
        dialog.set_modal(True)
        dialog.set_resizable(False)

        root = self.get_root()
        if isinstance(root, Gtk.Window):
            dialog.set_transient_for(root)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(16)
        content.set_margin_bottom(8)
        content.set_margin_start(24)
        content.set_margin_end(24)

        phase_label = Gtk.Label(label=PHASE_LABELS.get(self.phase, self.phase) + ' finished!')
        _apply_css(phase_label, f"""
            label {{
                color: {TEXT};
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        content.append(phase_label)

        if self.phase == 'work':
            self._dialog_add_button(dialog, content, '☕ Take Short Break',
                                    lambda: self._transition_to('short_break', dialog))
            self._dialog_add_button(dialog, content, '⏹ Stop',
                                    lambda: self._transition_to(None, dialog))
        else:
            self._dialog_add_button(dialog, content, '▶ Start Work Session',
                                    lambda: self._transition_to('work', dialog))
            self._dialog_add_button(dialog, content, '⏹ Stop',
                                    lambda: self._transition_to(None, dialog))

        dialog.present()

    def _dialog_add_button(self, dialog, content_area, label: str, callback):
        btn = Gtk.Button(label=label)
        _apply_css(btn, f"""
            button {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT};
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                padding: 8px 16px;
                min-height: 0;
                margin-bottom: 4px;
            }}
            button:hover {{
                background: {BORDER};
            }}
        """)
        btn.connect('clicked', lambda _: callback())
        content_area.append(btn)

    def _transition_to(self, next_phase: str | None, dialog: Gtk.Dialog):
        dialog.close()
        if next_phase is None:
            self.phase         = 'work'
            self._reset_timer_values()
            self.btn_start_pause.set_icon_name('media-playback-start-symbolic')
            self.drawing_area.queue_draw()
            return

        self.phase           = next_phase
        self._phase_start_dt = None
        self._reset_timer_values()
        self.drawing_area.queue_draw()
        self._start_timer()

    def _apply_duration_change(self, target_phase: str):
        if self.phase == target_phase:
            old_total = self.total_seconds
            new_total = self._seconds_for_phase(self.phase)
            diff = new_total - old_total
            self.total_seconds = new_total
            self.remaining_seconds = max(0, self.remaining_seconds + diff)
            
            if not self._is_active and self._bg_source is not None:
                GLib.source_remove(self._bg_source)
                self._bg_source = None
                if self.remaining_seconds > 0:
                    self._bg_source = GLib.timeout_add(self.remaining_seconds * 1000, self._on_bg_timeout)
                else:
                    self._on_bg_timeout()
                    
            self.drawing_area.queue_draw()

    def _on_work_changed(self, val):
        self.state.work_duration = val
        self.state.save_debounced()
        self._apply_duration_change('work')

    def _on_short_changed(self, val):
        self.state.short_break = val
        self.state.save_debounced()
        self._apply_duration_change('short_break')

    def _send_notification(self):
        phase_label = PHASE_LABELS.get(self.phase, self.phase)
        body_map = {
            'work':        'Time for a break!',
            'short_break': 'Break over – back to work!',
        }
        body = body_map.get(self.phase, 'Timer finished.')
        try:
            gi.require_version('Notify', '0.7')
            from gi.repository import Notify
            if not Notify.is_initted():
                Notify.init('LPA')
            notif = Notify.Notification.new(f'LPA – {phase_label}', body, 'dialog-information')
            notif.show()
        except Exception:
            pass

    def _play_chime(self):
        here       = os.path.dirname(os.path.abspath(__file__))
        bell_path  = os.path.join(here, '..', 'assets', 'bell.wav')
        bell_path  = os.path.normpath(bell_path)
        
        if os.path.isfile(bell_path):
            if not hasattr(self, '_chime_player'):
                import gi
                try:
                    gi.require_version('Gst', '1.0')
                    from gi.repository import Gst
                    if not Gst.is_initialized():
                        Gst.init(None)
                    self._chime_player = Gst.ElementFactory.make("playbin", "chime_player")
                    if self._chime_player:
                        self._chime_player.set_property("flags", 2)
                        bus = self._chime_player.get_bus()
                        bus.add_signal_watch()
                        def on_eos(bus, msg):
                            self._chime_player.set_state(Gst.State.READY)
                        bus.connect("message::eos", on_eos)
                except Exception as exc:
                    print(f"[PomodoroTab] Could not initialize chime player: {exc}")
                    self._chime_player = None

            if getattr(self, '_chime_player', None):
                from gi.repository import Gst
                self._chime_player.set_state(Gst.State.READY)
                import pathlib
                uri = pathlib.Path(bell_path).absolute().as_uri()
                self._chime_player.set_property("uri", uri)
                self._chime_player.set_state(Gst.State.PLAYING)
