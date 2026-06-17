import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

import os

from ui.pomodoro_tab import PomodoroTab
from ui.lofi_tab import LoFiTab
from ui.ambience_tab import AmbienceTab
from ui.theme_manager import ThemeManager

class MainWindow(Gtk.ApplicationWindow):

    def __init__(
        self,
        app,
        state,
        lofi_player,
        ambience_player,
        app_dir: str,
    ):
        super().__init__(application=app)

        self._state = state

        self._theme_manager = ThemeManager(self._state) #vulture: ignore
        self._load_css(app_dir)
        self.set_title('lpa')
        self.set_default_size(800, 600)
        self.set_resizable(False)
        self.connect('close-request', self._on_close_request)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        logo_img = Gtk.Image.new_from_file(os.path.join(app_dir, 'assets', 'logo.png'))
        logo_img.set_pixel_size(48)
        header_box.append(logo_img)
        
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)
        
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header_box.append(settings_btn)
        
        main_box.append(header_box)
        
        dashboard_grid = Gtk.Grid()
        dashboard_grid.set_column_spacing(8)
        dashboard_grid.set_row_spacing(8)
        dashboard_grid.set_vexpand(True)
        dashboard_grid.set_hexpand(True)

        self.pomodoro_tab = PomodoroTab(state)
        self.pomodoro_tab.add_css_class("dashboard-panel")
        self.pomodoro_tab.set_hexpand(True)
        self.pomodoro_tab.set_vexpand(True)
        dashboard_grid.attach(self.pomodoro_tab, 0, 0, 1, 1)

        self.lofi_tab = LoFiTab(state, lofi_player)
        self.lofi_tab.add_css_class("dashboard-panel")
        self.lofi_tab.set_hexpand(True)
        self.lofi_tab.set_vexpand(True)
        dashboard_grid.attach(self.lofi_tab, 1, 0, 1, 1)

        sounds_dir = os.path.join(app_dir, 'sounds')
        self.ambience_tab = AmbienceTab(state, ambience_player, sounds_dir)
        self.ambience_tab.add_css_class("dashboard-panel")
        self.ambience_tab.set_hexpand(True)
        self.ambience_tab.set_vexpand(True)
        dashboard_grid.attach(self.ambience_tab, 0, 1, 2, 1)

        main_box.append(dashboard_grid)

        self.set_child(main_box)
        self.connect('notify::is-active', self._on_active_changed)

    def _on_active_changed(self, window, param):
        active = window.is_active()
        self.pomodoro_tab.set_active(active)
        self.lofi_tab.set_active(active)

    def _load_css(self, app_dir: str) -> None:
        css_path = os.path.join(app_dir, 'assets', 'styles', 'app.css')

        if not os.path.exists(css_path):
            return

        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(css_path)
        except Exception:
            return

        display = Gdk.Display.get_default()
        if display is None:
            return

        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _on_settings_clicked(self, button):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, self._state)
        dialog.present()

    def _on_close_request(self, *_args) -> bool:
        self.hide()
        return True

    def show_window(self) -> None:
        self.present()
