from __future__ import annotations

import json
from pathlib import Path

import pytest

from glyph.models.preset import (
    SLOT_IDS,
    Alignment,
    Preset,
    SlotKind,
    bundled_default_path,
    default_preset,
    list_presets,
    presets_dir,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "presets" / "default.json"


def test_default_json_loads() -> None:
    from_file = Preset.load(DEFAULT_JSON)
    assert from_file.name
    assert set(from_file.slots) == set(SLOT_IDS)


def test_bundled_path_points_at_repo_preset() -> None:
    assert bundled_default_path() == DEFAULT_JSON
    assert bundled_default_path().is_file()


def test_save_omits_inactive_kind_fields(tmp_path: Path) -> None:
    preset = default_preset()
    path = tmp_path / "review.json"
    preset.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    text = raw["slots"]["top-left"]
    logo = raw["slots"]["bottom-middle"]
    assert "lines" in text
    assert "image" not in text
    assert "image" in logo
    assert "lines" not in logo


def test_fps_and_tokens_roundtrip(tmp_path: Path) -> None:
    preset = default_preset()
    preset.fps = 23.976
    preset.tokens["shot"] = "sh040"
    preset.tokens["note"] = "v12"
    path = tmp_path / "shot.json"
    preset.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["fps"] == 23.976
    assert raw["tokens"]["shot"] == "sh040"
    assert raw["tokens"]["note"] == "v12"
    loaded = Preset.load(path)
    assert loaded.fps == 23.976
    assert loaded.tokens["shot"] == "sh040"
    assert loaded.tokens["note"] == "v12"


def test_old_preset_without_tokens_gets_defaults() -> None:
    preset = Preset.from_json({"name": "legacy"})
    assert preset.fps == 24.0
    assert preset.tokens["shot"] == "ep01_sh010"
    assert preset.tokens["note"] == ""


def test_invalid_fps_falls_back() -> None:
    assert Preset.from_json({"fps": 0}).fps == 24.0
    assert Preset.from_json({"fps": -12}).fps == 24.0
    assert Preset.from_json({"fps": "nope"}).fps == 24.0
    assert Preset.from_json({"fps": None}).fps == 24.0


def test_custom_token_keys_are_kept() -> None:
    preset = Preset.from_json(
        {"tokens": {"shot": "sh010", "note": "v1", "client": "acme"}}
    )
    assert preset.tokens["shot"] == "sh010"
    assert preset.tokens["note"] == "v1"
    assert preset.tokens["client"] == "acme"


def test_bundled_presets_include_fps_and_tokens() -> None:
    for path in presets_dir().glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data["fps"], (int, float))
        assert float(data["fps"]) > 0
        assert "shot" in data["tokens"]
        assert "note" in data["tokens"]
        loaded = Preset.load(path)
        assert loaded.fps == float(data["fps"])
        assert loaded.tokens["shot"] == str(data["tokens"]["shot"])
        assert loaded.tokens["note"] == str(data["tokens"]["note"])


def test_roundtrip_file(tmp_path: Path) -> None:
    original = default_preset()
    path = tmp_path / "out.json"
    original.save(path)
    loaded = Preset.load(path)
    assert loaded.to_json() == original.to_json()


def test_missing_slots_get_empty_defaults() -> None:
    preset = Preset.from_json({"name": "blank"})
    assert preset.name == "blank"
    assert set(preset.slots) == set(SLOT_IDS)
    assert preset.slot("top-middle").kind is SlotKind.TEXT
    assert preset.slot("top-middle").lines == []
    assert preset.slot("top-left").alignment is Alignment.LEFT
    assert preset.slot("top-middle").alignment is Alignment.CENTER
    assert preset.slot("top-right").alignment is Alignment.RIGHT


def test_style_falls_back_on_bad_rgba() -> None:
    preset = Preset.from_json({"style": {"background": [1, 2], "font_color": None}})
    assert preset.style.background == (0, 0, 0, 160)
    assert preset.style.font_color == (255, 255, 255, 255)


def test_session_keeps_both_text_and_logo_until_save() -> None:
    preset = default_preset()
    slot = preset.slot("bottom-middle")
    slot.lines = ["kept"]
    slot.kind = SlotKind.TEXT
    raw = slot.to_json()
    assert raw["kind"] == "text"
    assert raw["lines"] == ["kept"]
    assert "image" not in raw
    assert slot.image == "studio.png"


def test_list_presets_uses_json_name(tmp_path: Path) -> None:
    default_preset().save(tmp_path / "default.json")
    other = default_preset()
    other.name = "client"
    other.save(tmp_path / "client.json")
    labels = [label for label, path in list_presets(tmp_path)]
    assert "review" in labels
    assert "client" in labels
    assert len(labels) == 2


def test_presets_dir_is_repo_presets() -> None:
    assert presets_dir() == DEFAULT_JSON.parent
    names = {label for label, _path in list_presets()}
    assert "review" in names


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Preset.load(tmp_path / "nope.json")
