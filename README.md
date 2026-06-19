<div align="center">
  <img src="assets/logo.png" alt="LPA Logo" width="128" />
</div>

# LPA

![License](https://img.shields.io/github/license/mareomanoj6/lpa)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

A little something I made to get a 12LPA job... Lo-fi, ambient sounds, and a Pomodoro timer. What else do you need?

## Table of Contents
- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Folder Structure](#folder-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Thanks](#thanks)

## About
<!-- Add your about section here -->

## Features
- **Pomodoro Timer**: Customisable phases including Work, Short Break, and Long Break.
- **Lo-Fi Radio**: Integrated Lo-Fi streaming via YouTube and internet radio.
- **Ambient Sound Mixer**: Create your ideal soundscape with multi-channel audio support.
- **System Tray**: Quick and easy access to the app from your system tray.

## Installation

### Via Flatpak (Recommended)
LPA is packaged as a Flatpak. You can build and install it locally using `flatpak-builder`:

```bash
# Add Flathub repository if you haven't already
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Build and install the flatpak
flatpak-builder --user --install --force-clean build-dir io.github.mareomanoj6.lpa.json
```

### Running from Source
If you prefer not to use Flatpak, you can run the application directly using Python. First, ensure you have the required dependencies installed:
- Python 3
- GTK 4 (`gir1.2-gtk-4.0`)
- PyGObject (`python3-gi`)
- `yt-dlp` (`pip install yt-dlp`)
- `libayatana-appindicator3` (for the system tray icon)

Then, simply run the main script from the root of the repository:
```bash
python3 lpa.py
```

Or you could just download the release from the [Releases page](https://github.com/mareomanoj6/lpa/releases).

## Usage

Once installed, you can launch LPA from your application menu or run it from the terminal:

```bash
flatpak run io.github.mareomanoj6.lpa
```

Use the built-in interface to set your Pomodoro timers, pick a Lo-Fi stream, or mix ambient sounds to help you focus or relax.

## Folder Structure

```text
lpa/
├── assets/
│   ├── styles/
│   │   └── app.css
│   ├── bell.wav
│   └── logo.png
├── audio/
│   ├── mpris.py
│   └── player.py
├── data/
│   └── state.py
├── sounds/
│   ├── cafe.ogg
│   ├── farm.ogg
│   ├── fireplace.ogg
│   ├── rain.ogg
│   ├── train.ogg
│   └── wind.ogg
├── tray/
│   ├── tray_icon.py
│   └── tray_process.py
├── ui/
│   ├── ambience_tab.py
│   ├── lofi_tab.py
│   ├── main_window.py
│   ├── pomodoro_tab.py
│   ├── settings_dialog.py
│   └── theme_manager.py
├── lpa.py
├── io.github.mareomanoj6.lpa.desktop
├── io.github.mareomanoj6.lpa.json
├── io.github.mareomanoj6.lpa.metainfo.xml
├── libayatana-appindicator-gtk3.json
├── python3-yt-dlp.json
├── flatpak-pip-generator
├── LICENSE
├── LICENSE.CC0
└── README.md
```

## Roadmap
- [ ] Advanced timer configurations
- [ ] Expand to Web, Android, Windows and iOS.
- [ ] Polish UI
- [ ] Add keyboard shortcuts

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the [GPL-3.0-or-later License](https://spdx.org/licenses/GPL-3.0-or-later.html). 
Metadata is licensed under CC0-1.0.

## Thanks
Thanks to [Blanket](https://github.com/rafaelmardojai/blanket), for giving me an initial inspiration to bring everything I needed into one interface.
