# LPA

LPA is a GTK4 productivity and ambient audio application designed for Linux. It combines a Pomodoro timer with a multi-channel audio engine capable of playing Lo-Fi streams, internet radio, and local ambient sounds simultaneously.

## Features

- **Pomodoro Timer**: Customizable sessions, work and break times, and a progress ring to see how much time has elapsed.
- **Audio Streams**: Stream internet radio and YouTube audio using `yt-dlp`. (3 YT streams and 1 internet radio built in)
- **Ambient Mixer**: Multi-channel ambient sounds with individiual volume controls. (6 built-in sounds)
- **System Integration**: Native GTK4 interface, MPRIS media controls, desktop notifications, and a system tray icon.

## Installation

### Pre-built Flatpak (Recommended)

The easiest way to install LPA is to download the pre-built `lp.flatpak` bundle from the **Releases** page of this repository.

```bash
flatpak install lp.flatpak
```

### Build Flatpak from Source

```bash
flatpak-builder --user --install --force-clean build-dir io.github.mareomanoj6.lpa.json
flatpak run io.github.mareomanoj6.lpa
```

### Manual Installation
To run LPA directly from source, install the following dependencies:

**Debian/Ubuntu:**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-notify-0.7 libnotify-dev libayatana-appindicator3-1 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly python3-dbus
```

**Arch Linux:**
```bash
sudo pacman -S python-gobject python-cairo gtk4 libnotify libayatana-appindicator gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly python-dbus
```

Then install the Python dependency and run:
```bash
pip install yt-dlp
python3 lpa.py
```

## Configuration and Data

State, session logs, and custom audio files are stored in the standard XDG data directory:
- **Native**: `~/.local/share/lpa/`
- **Flatpak**: `~/.var/app/io.github.mareomanoj6.lpa/data/lpa/`

## License
GPL 3.0
