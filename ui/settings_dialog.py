import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

import os
import shutil

class SettingsDialog(Gtk.Window):
    def __init__(self, parent, state):
        super().__init__()
        self.set_title("settings")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(700, 500)
        self.state = state
        self.parent_window = parent

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(False)
        self.set_titlebar(header)
        
        title_lbl = Gtk.Label(label="settings")
        title_lbl.add_css_class("title-large")
        header.set_title_widget(title_lbl)
        
        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda b: self.close())
        header.pack_end(close_btn)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        lists_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        lists_box.set_vexpand(True)
        lists_box.set_hexpand(True)

        streams_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        streams_vbox.set_hexpand(True)
        
        streams_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        streams_lbl = Gtk.Label(label="streams:")
        streams_lbl.set_halign(Gtk.Align.START)
        streams_lbl.add_css_class("title-medium")
        streams_header.append(streams_lbl)
        
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        streams_header.append(spacer)
        
        add_s_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_s_btn.add_css_class("icon-button")
        add_s_btn.connect("clicked", self._on_add_stream)
        streams_header.append(add_s_btn)
        
        edit_s_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_s_btn.add_css_class("icon-button")
        edit_s_btn.connect("clicked", self._on_edit_stream)
        streams_header.append(edit_s_btn)
        
        del_s_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_s_btn.add_css_class("icon-button")
        del_s_btn.connect("clicked", self._on_remove_stream)
        streams_header.append(del_s_btn)
        
        streams_vbox.append(streams_header)
        
        streams_scroll = Gtk.ScrolledWindow()
        streams_scroll.set_vexpand(True)
        self.streams_list = Gtk.ListBox()
        self.streams_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.streams_list.add_css_class("settings-list")
        streams_scroll.set_child(self.streams_list)
        streams_vbox.append(streams_scroll)
        
        lists_box.append(streams_vbox)

        sounds_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sounds_vbox.set_hexpand(True)
        
        sounds_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sounds_lbl = Gtk.Label(label="sounds:")
        sounds_lbl.set_halign(Gtk.Align.START)
        sounds_lbl.add_css_class("title-medium")
        sounds_header.append(sounds_lbl)
        
        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        sounds_header.append(spacer2)
        
        add_snd_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_snd_btn.add_css_class("icon-button")
        add_snd_btn.connect("clicked", self._on_add_sound)
        sounds_header.append(add_snd_btn)

        del_snd_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_snd_btn.add_css_class("icon-button")
        del_snd_btn.connect("clicked", self._on_remove_sound)
        sounds_header.append(del_snd_btn)
        
        sounds_vbox.append(sounds_header)
        
        sounds_scroll = Gtk.ScrolledWindow()
        sounds_scroll.set_vexpand(True)
        self.sounds_list = Gtk.ListBox()
        self.sounds_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sounds_list.add_css_class("settings-list")
        sounds_scroll.set_child(self.sounds_list)
        sounds_vbox.append(sounds_scroll)
        
        lists_box.append(sounds_vbox)

        main_box.append(lists_box)
        self.set_child(main_box)

        self._refresh_streams_list()
        self._refresh_sounds_list()

    def _refresh_streams_list(self):
        while self.streams_list.get_first_child() is not None:
            self.streams_list.remove(self.streams_list.get_first_child())
            
        streams = getattr(self.state, 'custom_streams', []) or []
        for i, stream in enumerate(streams):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            
            name_lbl = Gtk.Label(label=f"{i+1}. {stream.get('name', 'Unknown')}")
            name_lbl.set_halign(Gtk.Align.START)
            vbox.append(name_lbl)
            
            url_lbl = Gtk.Label(label=stream.get('url', ''))
            url_lbl.set_halign(Gtk.Align.START)
            url_lbl.add_css_class("muted")
            vbox.append(url_lbl)
            
            list_row = Gtk.ListBoxRow()
            list_row.set_child(vbox)
            list_row._stream_index = i
            self.streams_list.append(list_row)

    def _get_selected_stream_idx(self):
        row = self.streams_list.get_selected_row()
        if row is not None:
            return getattr(row, '_stream_index', -1)
        return -1

    def _on_remove_stream(self, button):
        idx = self._get_selected_stream_idx()
        streams = getattr(self.state, 'custom_streams', []) or []
        if 0 <= idx < len(streams):
            streams.pop(idx)
            self.state.custom_streams = streams
            self.state.save()
            self._refresh_streams_list()
            self.parent_window.lofi_tab._refresh_streams()

    def _on_add_stream(self, button):
        self._show_stream_dialog(None, -1)

    def _on_edit_stream(self, button):
        idx = self._get_selected_stream_idx()
        streams = getattr(self.state, 'custom_streams', []) or []
        if 0 <= idx < len(streams):
            self._show_stream_dialog(streams[idx], idx)

    def _show_stream_dialog(self, stream_data, idx):
        dialog = Gtk.Dialog(title="Stream", transient_for=self, modal=True)
        dialog.set_default_size(350, -1)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        
        name_entry = Gtk.Entry(placeholder_text="Stream Name")
        if stream_data: name_entry.set_text(stream_data.get('name', ''))
        content.append(name_entry)
        
        url_entry = Gtk.Entry(placeholder_text="Stream URL")
        if stream_data: url_entry.set_text(stream_data.get('url', ''))
        content.append(url_entry)
        
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.ACCEPT)
        
        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                name = name_entry.get_text()
                url = url_entry.get_text()
                if name and url:
                    streams = getattr(self.state, 'custom_streams', []) or []
                    stype = 'youtube' if 'youtube.com' in url or 'youtu.be' in url else 'radio'
                    if stream_data and 0 <= idx < len(streams):
                        streams[idx] = {"name": name, "url": url, "type": stype}
                    else:
                        streams.append({"name": name, "url": url, "type": stype})
                    self.state.custom_streams = streams
                    self.state.save()
                    self._refresh_streams_list()
                    self.parent_window.lofi_tab._refresh_streams()
            dlg.destroy()
            
        dialog.connect("response", on_response)
        dialog.show()

    def _refresh_sounds_list(self):
        while self.sounds_list.get_first_child() is not None:
            self.sounds_list.remove(self.sounds_list.get_first_child())
            
        from ui.ambience_tab import BUILTIN_SOUNDS
        custom = getattr(self.state, 'custom_ambient_sounds', []) or []
        
        all_sounds = []
        for bs in BUILTIN_SOUNDS:
            all_sounds.append({"name": bs["name"], "path": "Built-in", "_is_builtin": True})
        all_sounds.extend(custom)
            
        for i, sound in enumerate(all_sounds):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            
            name_lbl = Gtk.Label(label=sound.get("name", "Unknown"))
            name_lbl.set_halign(Gtk.Align.START)
            vbox.append(name_lbl)
            
            path_lbl = Gtk.Label(label=sound.get("path", ""))
            path_lbl.set_halign(Gtk.Align.START)
            path_lbl.add_css_class("muted")
            path_lbl.set_ellipsize(gi.repository.Pango.EllipsizeMode.MIDDLE)
            vbox.append(path_lbl)
            
            list_row = Gtk.ListBoxRow()
            list_row.set_child(vbox)
            list_row._sound_index = i
            self.sounds_list.append(list_row)

    def _get_selected_sound_idx(self):
        row = self.sounds_list.get_selected_row()
        if row is not None:
            return getattr(row, '_sound_index', -1)
        return -1

    def _on_remove_sound(self, button):
        idx = self._get_selected_sound_idx()
        from ui.ambience_tab import BUILTIN_SOUNDS
        custom_idx = idx - len(BUILTIN_SOUNDS)
        if custom_idx >= 0:
            sounds = getattr(self.state, 'custom_ambient_sounds', []) or []
            if 0 <= custom_idx < len(sounds):
                sounds.pop(custom_idx)
                self.state.custom_ambient_sounds = sounds
                self.state.save()
                self._refresh_sounds_list()
                self._reload_ambience_tab()

    def _on_add_sound(self, button):
        chooser = Gtk.FileChooserDialog(
            title="Select Audio File",
            action=Gtk.FileChooserAction.OPEN,
            transient_for=self,
            modal=True
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button("Open", Gtk.ResponseType.ACCEPT)
        
        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                file_obj = dlg.get_file()
                src_path = file_obj.get_path() if file_obj else None
                if src_path:
                    try:
                        dest_dir = os.path.join(self.state.get_data_dir(), 'sounds')
                    except AttributeError:
                        dest_dir = os.path.expanduser('~/.local/share/lpa/sounds')
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    basename = os.path.basename(src_path)
                    dest_path = os.path.join(dest_dir, basename)
                    if src_path != dest_path:
                        try:
                            shutil.copy2(src_path, dest_path)
                        except Exception:
                            pass
                            
                    name_no_ext = os.path.splitext(basename)[0]
                    sound_id = name_no_ext.lower().replace(' ', '_')
                    display_name = name_no_ext.replace('_', ' ').replace('-', ' ').title()
                    
                    sounds = getattr(self.state, 'custom_ambient_sounds', []) or []
                    sounds.append({
                        "id": sound_id,
                        "name": display_name,
                        "path": dest_path
                    })
                    self.state.custom_ambient_sounds = sounds
                    self.state.save()
                    self._refresh_sounds_list()
                    self._reload_ambience_tab()
            dlg.destroy()
            
        chooser.connect("response", on_response)
        chooser.present()

    def _reload_ambience_tab(self):
        tab = self.parent_window.ambience_tab
        while tab.flow.get_first_child() is not None:
            tab.flow.remove(tab.flow.get_first_child())
        tab._sound_paths.clear()
        tab._sliders.clear()
        tab._load_sounds()
