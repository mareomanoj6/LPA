import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

import os

BUILTIN_SOUNDS = [
    {'id': 'rain',       'name': 'rain',        'file': 'rain.ogg'},
    {'id': 'fireplace',  'name': 'fireplace',   'file': 'fireplace.ogg'},
    {'id': 'cafe',       'name': 'cafe',        'file': 'cafe.ogg'},
    {'id': 'farm',       'name': 'farm',        'file': 'farm.ogg'},
    {'id': 'wind',       'name': 'wind',        'file': 'wind.ogg'},
    {'id': 'train',      'name': 'train',       'file': 'train.ogg'},
]

class AmbienceTab(Gtk.Box):

    def __init__(self, state, player, app_sounds_dir: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.state          = state
        self.player         = player
        self.app_sounds_dir = app_sounds_dir

        self._sound_paths: dict[str, str] = {}
        self._sliders: dict[str, Gtk.Scale] = {}

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_valign(Gtk.Align.CENTER)
        main_vbox.set_vexpand(True)
        
        title = Gtk.Label(label="ambience")
        title.add_css_class("title-medium")
        main_vbox.append(title)
        
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(False)
        self.flow.set_column_spacing(16)
        self.flow.set_row_spacing(16)
        self.flow.set_halign(Gtk.Align.CENTER)
        self.flow.add_css_class("ambience-flow")
        main_vbox.append(self.flow)
         
        self.append(main_vbox)

        self._load_sounds()
        self._restore_state()

    def _load_sounds(self):
        custom = getattr(self.state, 'custom_ambient_sounds', []) or []
        total_sounds = len(BUILTIN_SOUNDS) + len(custom)
        
        if total_sounds <= 4:
            cols = 2
        elif total_sounds <= 6:
            cols = 3
        else:
            cols = 4
            
        self.flow.set_min_children_per_line(cols)
        self.flow.set_max_children_per_line(cols)

        for sound in BUILTIN_SOUNDS:
            full_path = os.path.join(self.app_sounds_dir, sound['file'])
            self._register_and_add_slider(
                sound_id=sound['id'],
                name=sound['name'],
                full_path=full_path
            )

        for csound in custom:
            sound_id  = csound.get('id', csound.get('name', '').lower().replace(' ', '_'))
            full_path = csound.get('path', '')
            name      = csound.get('name', os.path.splitext(os.path.basename(full_path))[0])
            if os.path.isfile(full_path):
                self._register_and_add_slider(
                    sound_id=sound_id,
                    name=name,
                    full_path=full_path
                )

    def _register_and_add_slider(self, sound_id: str, name: str, full_path: str):
        self._sound_paths[sound_id] = full_path

        vols    = getattr(self.state, 'ambient_volumes', {}) or {}
        init_vol = int(vols.get(sound_id, 0)) 
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_halign(Gtk.Align.CENTER)
        
        lbl = Gtk.Label(label=name.lower())
        lbl.add_css_class("ambience-label")
        vbox.append(lbl)
        
        slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        slider.set_draw_value(False)
        slider.set_value(init_vol)
        slider.set_size_request(120, -1)
        slider.add_css_class("ambience-slider")
        slider.connect('value-changed', lambda sc, sid=sound_id: self._on_volume_changed(sid, sc))
        vbox.append(slider)

        self._sliders[sound_id] = slider

        child = Gtk.FlowBoxChild()
        child.set_child(vbox)
        child.set_focusable(False)
        self.flow.append(child)

    def _restore_state(self):
        vols = getattr(self.state, 'ambient_volumes', {}) or {}
        for sound_id, vol in vols.items():
            if vol > 0 and sound_id in self._sound_paths:
                try:
                    self.player.set_volume(sound_id, vol)
                except Exception:
                    pass

    def _on_volume_changed(self, sound_id: str, scale: Gtk.Scale):
        value = int(scale.get_value())
        full_path = self._sound_paths.get(sound_id, '')
        
        if value > 0:
            if not self.player.is_playing(sound_id):
                if full_path and os.path.isfile(full_path):
                    try:
                        self.player.play(sound_id, full_path)
                    except Exception:
                        pass
            try:
                self.player.set_volume(sound_id, value)
            except Exception:
                pass
        else:
            try:
                self.player.stop(sound_id)
            except Exception:
                pass

        vols = getattr(self.state, 'ambient_volumes', {}) or {}
        vols[sound_id] = value
        self.state.ambient_volumes = vols
        try:
            self.state.save_debounced()
        except Exception:
            pass
