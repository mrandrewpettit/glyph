from __future__ import annotations

from pathlib import Path

import pytest

from glyph.launch import parse_launch
from glyph.media.loader import collect_input
from glyph.models.preset import default_preset, resolve_preset_arg


def test_parse_launch_maya_style() -> None:
    launch, qt = parse_launch(
        [
            "glyph",
            r"D:\playblasts\sh010",
            "--shot",
            "ep01_sh010",
            "--preset",
            "prorigs",
        ]
    )
    assert launch.path == r"D:\playblasts\sh010"
    assert launch.shot == "ep01_sh010"
    assert launch.preset == "prorigs"
    assert qt == ["glyph"]


def test_parse_launch_short_flags_and_qt_rest() -> None:
    launch, qt = parse_launch(
        ["glyph", "-s", "shotA", "-p", "review", "--style", "Fusion"]
    )
    assert launch.shot == "shotA"
    assert launch.preset == "review"
    assert launch.path is None
    assert qt == ["glyph", "--style", "Fusion"]


def test_parse_launch_input_flag() -> None:
    launch, _qt = parse_launch(["glyph", "-i", r"D:\out\hero.png", "--shot", "sh010"])
    assert launch.path == r"D:\out\hero.png"
    assert launch.shot == "sh010"


def test_collect_input_file(tmp_path: Path) -> None:
    still = tmp_path / "hero.png"
    still.write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("nope")
    assert collect_input(still) == [still.resolve()]


def test_collect_input_directory_is_sequence(tmp_path: Path) -> None:
    (tmp_path / "clip.1002.png").write_bytes(b"x")
    (tmp_path / "clip.1001.png").write_bytes(b"x")
    (tmp_path / "readme.txt").write_text("skip")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "other.png").write_bytes(b"x")
    files = collect_input(tmp_path)
    assert [path.name for path in files] == ["clip.1001.png", "clip.1002.png"]


def test_collect_input_empty_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no image files"):
        collect_input(tmp_path)


def test_resolve_preset_by_stem_and_path(tmp_path: Path) -> None:
    preset = default_preset()
    preset.name = "client look"
    dest = tmp_path / "prorigs.json"
    preset.save(dest)
    assert resolve_preset_arg("prorigs", tmp_path) == dest.resolve()
    assert resolve_preset_arg("client look", tmp_path) == dest.resolve()
    assert resolve_preset_arg(str(dest), tmp_path) == dest.resolve()


def test_resolve_preset_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="preset not found"):
        resolve_preset_arg("nope", tmp_path)
