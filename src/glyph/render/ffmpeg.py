from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from glyph.platform import which_ffmpeg


class FFmpegError(RuntimeError):
    pass


def encode_png_sequence(
    frames_dir: Path,
    dest: Path,
    fps: float,
) -> None:
    ffmpeg = which_ffmpeg()
    if ffmpeg is None:
        raise FFmpegError("ffmpeg was not found on PATH")
    rate = _fps_arg(fps)
    pattern = str(frames_dir / "frame_%04d.png")
    cmd = [
        str(ffmpeg),
        "-y",
        "-framerate",
        rate,
        "-i",
        pattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    kwargs: dict[str, object] = {
        "capture_output": True,
        "text": True,
        "check": False,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise FFmpegError(err[-2000:])


def _fps_arg(fps: float) -> str:
    if abs(fps - 23.976) < 0.01:
        return "24000/1001"
    if float(fps).is_integer():
        return str(int(fps))
    return str(fps)
