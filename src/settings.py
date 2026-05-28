from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass, asdict

_BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
_SETTINGS_PATH = os.path.join(_BASE_DIR, "settings.json")


@dataclass
class AppSettings:
    blink_enabled:   bool  = True
    blink_threshold: float = 5.0   # seconds
    sit_enabled:     bool  = True
    sit_threshold:   int   = 30    # minutes
    water_enabled:   bool  = True
    water_threshold: int   = 30    # minutes

    @property
    def sit_threshold_sec(self) -> float:
        return self.sit_threshold * 60.0

    @property
    def water_threshold_sec(self) -> float:
        return self.water_threshold * 60.0

    def save(self) -> None:
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> AppSettings:
        if os.path.exists(_SETTINGS_PATH):
            try:
                with open(_SETTINGS_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                valid = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
                return cls(**valid)
            except Exception:
                pass
        return cls()
