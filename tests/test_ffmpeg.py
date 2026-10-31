from pathlib import Path

import pytest

from glyph.render import ffmpeg as ffmpeg_mod
from glyph.render.ffmpeg import FFmpegError, _fps_arg, encode_png_sequence


def test_fps_arg_ntsc_and_integers() -> None:
    assert _fps_arg(23.976) == "24000/1001"
    assert _fps_arg(24.0) == "24"
    assert _fps_arg(25) == "25"
    assert _fps_arg(29.97) == "29.97"


def test_encode_raises_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ffmpeg_mod, "which_ffmpeg", lambda: None)
    with pytest.raises(FFmpegError, match="not found"):
        encode_png_sequence(tmp_path, tmp_path / "out.mov", 24)


def test_encode_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ffmpeg_mod, "which_ffmpeg", lambda: Path("ffmpeg"))

    class Result:
        returncode = 1
        stderr = "encoder exploded"
        stdout = ""

    monkeypatch.setattr(ffmpeg_mod.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(FFmpegError, match="encoder exploded"):
        encode_png_sequence(tmp_path, tmp_path / "out.mov", 24)
