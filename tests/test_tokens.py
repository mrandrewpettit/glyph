from glyph.models.tokens import TokenContext, resolve_line, timecode


def test_shot_and_filename() -> None:
    ctx = TokenContext(filename="hero.png", shot="ep01_sh010")
    assert resolve_line("{filename}", ctx) == "hero.png"
    assert resolve_line("{shot}", ctx) == "ep01_sh010"


def test_timecode_is_elapsed_runtime() -> None:
    assert timecode(0, 24) == "00:00:00.00"
    assert timecode(24, 24) == "00:00:01.00"
    assert timecode(1, 3) == "00:00:00.33"
    assert timecode(3, 3) == "00:00:01.00"
    assert timecode(23, 3) == "00:00:07.67"


def test_all_built_in_tokens() -> None:
    ctx = TokenContext(
        filename="a.1001.exr",
        shot="sh010",
        note="v03",
        date="2026-01-02",
        time="03:04:05",
        frame=1001,
        start_frame=1001,
        index=0,
        fps=24.0,
        width=2048,
        height=1080,
    )
    line = (
        "{filename} {shot} {note} {date} {time} {datetime} "
        "{frame} {timecode} {width} {height} {resolution} {fps}"
    )
    out = resolve_line(line, ctx)
    assert "a.1001.exr" in out
    assert "sh010" in out
    assert "v03" in out
    assert "2026-01-02 03:04:05" in out
    assert "2048x1080" in out
    assert "00:00:00.00" in out
    assert "{" not in out


def test_unknown_braces_left_alone() -> None:
    assert resolve_line("{nope}", TokenContext()) == "{nope}"
