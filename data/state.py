import json
import os
from pathlib import Path

_DEFAULT_STREAMS = [
    {
        "name": "chill beats (lofi girl)",
        "url": "https://www.youtube.com/@LofiGirl/live",
        "type": "youtube",
    },
    {
        "name": "coffee shop radio (steezyasfvck)",
        "url": "https://www.youtube.com/@steezyasfvck/live",
        "type": "youtube",
    },
    {
        "name": "chillhop radio",
        "url": "https://www.youtube.com/watch?v=5yx6BWlEVcY",
        "type": "youtube",
    },
    {
        "name": "(groove salad)",
        "url": "https://ice2.somafm.com/groovesalad-128-mp3",
        "type": "radio",
    },
]

_DEFAULTS = {
    "work_duration": 25,
    "short_break": 5,
    "lofi_volume": 70,
    "ambient_volumes": {},

    "custom_streams": _DEFAULT_STREAMS,
    "custom_ambient_sounds": [],
    "migrated_streams": False,
    "bg_color": "#151515",
    "text_color": "#ffffff",
    "accent_color": "#7492e5",

}


class State:
    def __init__(self, data: dict):
        self.work_duration: int = int(
            data.get("work_duration", _DEFAULTS["work_duration"])
        )
        self.short_break: int = int(data.get("short_break", _DEFAULTS["short_break"]))

        self.lofi_volume: int = int(data.get("lofi_volume", _DEFAULTS["lofi_volume"]))
        self.ambient_volumes: dict[str, int] = dict(
            data.get("ambient_volumes", _DEFAULTS["ambient_volumes"])
        )


        self.bg_color: str = str(data.get("bg_color", _DEFAULTS["bg_color"]))
        self.text_color: str = str(data.get("text_color", _DEFAULTS["text_color"]))
        self.accent_color: str = str(data.get("accent_color", _DEFAULTS["accent_color"]))


        self.custom_streams: list[dict] = list(data.get("custom_streams", []))
        self.custom_ambient_sounds: list[dict] = list(
            data.get("custom_ambient_sounds", _DEFAULTS["custom_ambient_sounds"])
        )

        self.migrated_streams = bool(data.get("migrated_streams", False))
        if not self.migrated_streams:
            self.custom_streams = _DEFAULT_STREAMS + self.custom_streams
            self.migrated_streams = True

        seen_urls = set()
        deduped = []
        for s in self.custom_streams:
            url = s.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(s)
        self.custom_streams = deduped

        self.data_dir: str = State.get_data_dir()

        self._save_timeout_id = None

    @staticmethod
    def get_data_dir() -> str:
        xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
        if not xdg_data_home:
            xdg_data_home = os.path.expanduser("~/.local/share")
        data_dir = Path(xdg_data_home) / "lpa"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    @staticmethod
    def _state_file_path() -> Path:
        return Path(State.get_data_dir()) / "state.json"

    @classmethod
    def load(cls) -> "State":
        path = cls._state_file_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                if isinstance(raw, dict):
                    return cls(raw)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[State] Warning: could not read {path}: {exc}")
        return cls({})

    def save(self) -> None:
        path = self._state_file_path()
        tmp_path = path.with_suffix(".json.tmp")

        def _clean_streams(streams):
            return [
                {k: v for k, v in s.items() if not k.startswith("_")} for s in streams
            ]

        payload = {
            "work_duration": self.work_duration,
            "short_break": self.short_break,
            "lofi_volume": self.lofi_volume,
            "ambient_volumes": self.ambient_volumes,
            "custom_streams": _clean_streams(self.custom_streams),
            "custom_ambient_sounds": self.custom_ambient_sounds,
            "migrated_streams": self.migrated_streams,
            "bg_color": self.bg_color,
            "text_color": self.text_color,
            "accent_color": self.accent_color,

        }

        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except OSError as exc:
            print(f"[State] Error: could not save state to {path}: {exc}")
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def save_debounced(self) -> None:
        import gi

        gi.require_version("GLib", "2.0")
        from gi.repository import GLib

        if self._save_timeout_id is not None:
            GLib.source_remove(self._save_timeout_id)

        self._save_timeout_id = GLib.timeout_add(500, self._on_save_timeout)

    def _on_save_timeout(self) -> bool:
        from gi.repository import GLib

        self._save_timeout_id = None
        self.save()
        return GLib.SOURCE_REMOVE


    def __repr__(self) -> str:
        return (
            f"State(work={self.work_duration}m, short={self.short_break}m, "
            f"lofi_vol={self.lofi_volume}, "
            f"custom_streams={len(self.custom_streams)}, "
            f"custom_ambient={len(self.custom_ambient_sounds)})"
        )
