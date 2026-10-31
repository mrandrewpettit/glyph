"""Windows font and FFmpeg lookup."""

from __future__ import annotations

import shutil
from pathlib import Path

_FONTS = (
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
)


def default_font_path() -> Path | None:
    for path in _FONTS:
        if path.is_file():
            return path
    return None


def which_ffmpeg() -> Path | None:
    found = shutil.which("ffmpeg")
    return Path(found) if found else None


def which_ffprobe() -> Path | None:
    found = shutil.which("ffprobe")
    return Path(found) if found else None
