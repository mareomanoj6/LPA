import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

class ThemeManager:
    def __init__(self, state):
        self._state = state
        self._provider = Gtk.CssProvider()
        
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self._provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
            
        self.apply_theme()

    def apply_theme(self):
        css = f"""
        @define-color bg_color {self._state.bg_color};
        @define-color text_color {self._state.text_color};
        @define-color accent_color {self._state.accent_color};
        @define-color muted_color alpha({self._state.text_color}, 0.5);
        
        window {{
            background-color: @bg_color;
            color: @text_color;
            font-family: 'Inter', 'Roboto', sans-serif;
        }}
        
        headerbar {{
            background-color: @bg_color;
            color: @text_color;
            border-bottom: 1px solid alpha(@text_color, 0.1);
            background-image: none;
        }}
        
        .dashboard-panel {{
            background-color: alpha(@text_color, 0.05);
            border: 1px solid alpha(@text_color, 0.1);
            border-radius: 16px;
            padding: 16px;
        }}
        
        button.flat {{
            background: transparent;
            border: none;
            color: @text_color;
            padding: 12px;
            border-radius: 50%;
        }}
        
        button.flat:hover {{
            background-color: alpha(@text_color, 0.1);
        }}
        
        button {{
            color: @text_color;
        }}
        
        .title-medium {{
            font-size: 18px;
            font-weight: bold;
            color: @text_color;
        }}
        
        .muted {{
            color: @muted_color;
            font-size: 12px;
        }}
        
        .stat-entry {{
            background: transparent;
            border: none;
            color: @text_color;
            font-size: 24px;
            font-weight: bold;
            box-shadow: none;
        }}
        
        .vol-slider trough {{
            background-color: alpha(@text_color, 0.1);
            border-radius: 8px;
            min-width: 8px;
        }}
        
        .vol-slider highlight {{
            background-color: @accent_color;
            border-radius: 8px;
        }}
        
        .ambience-flow {{
            background: transparent;
        }}
        
        .ambience-label {{
            color: @text_color;
            font-size: 12px;
            background-color: alpha(@text_color, 0.1);
            padding: 4px 12px;
            border-radius: 16px;
        }}
        
        .ambience-slider trough {{
            background-color: alpha(@text_color, 0.1);
            border-radius: 4px;
            min-height: 4px;
        }}
        
        .ambience-slider highlight {{
            background-color: @accent_color;
            border-radius: 4px;
        }}
        
        /* Dropdown and popover styling */
        dropdown > button {{
            background-color: alpha(@text_color, 0.05);
            color: @text_color;
            border: 1px solid alpha(@text_color, 0.1);
            border-radius: 8px;
        }}
        
        popover > contents {{
            background-color: @bg_color;
            color: @text_color;
            border: 1px solid alpha(@text_color, 0.1);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }}
        
        popover list {{
            background-color: transparent;
        }}
        
        popover list row {{
            padding: 8px 12px;
        }}
        
        popover list row:hover {{
            background-color: alpha(@text_color, 0.1);
        }}
        
        /* Settings list styling */
        .settings-list {{
            background-color: alpha(@text_color, 0.05);
            border: 1px solid alpha(@text_color, 0.1);
            border-radius: 8px;
            color: @text_color;
        }}
        
        .settings-list label {{
            color: @text_color;
        }}
        
        .settings-list row {{
            border-bottom: 1px solid alpha(@text_color, 0.05);
            padding: 8px;
        }}
        
        .settings-list row:last-child {{
            border-bottom: none;
        }}
        
        .icon-button {{
            background: transparent;
            border: none;
            color: @text_color;
            padding: 4px;
            border-radius: 4px;
        }}
        
        .icon-button:hover {{
            background-color: alpha(@text_color, 0.1);
        }}
        

        """
        self._provider.load_from_data(css.encode('utf-8'))
