from glyph.platform import default_font_path, which_ffmpeg, which_ffprobe


def test_windows_default_font_exists() -> None:
    font = default_font_path()
    assert font is not None
    assert font.is_file()
    assert font.suffix.lower() == ".ttf"


def test_ffmpeg_lookup_type() -> None:
    found = which_ffmpeg()
    if found is not None:
        assert found.name.lower().startswith("ffmpeg")
        assert found.is_file()
    probe = which_ffprobe()
    if probe is not None:
        assert probe.is_file()
