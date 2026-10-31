from pathlib import Path

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from glyph.launch import LaunchArgs
from glyph.main_window import MainWindow, _safe_filename
from glyph.models.preset import Preset, default_preset


def test_export_disabled_with_no_files(qapp: QApplication) -> None:
    del qapp
    window = MainWindow()
    assert window._title_files.text() == "No files"
    assert window._export_btn.isEnabled() is False
    assert window._job is None
    assert window._inspector._sequence_host.isHidden()


def test_tokens_use_job_when_media_loaded(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    from glyph.media.loader import infer_job
    from glyph.media.preview import load_plate

    path = _write_png(tmp_path / "plate.1012.png")
    window = MainWindow()
    window._load_paths([path])
    assert window._job is not None
    assert window._job.kind == "still"
    assert window._export_btn.isEnabled() is True
    assert window._title_files.text() == "plate.1012.png"
    tokens = window._tokens()
    assert tokens.filename == "plate.1012.png"
    assert tokens.frame == 1012
    assert tokens.width == 40
    assert tokens.height == 30
    assert infer_job([path]).start_frame == 1012
    assert not load_plate(path).isNull()
    assert tokens.shot == window._preset.tokens["shot"]
    assert tokens.note == window._preset.tokens["note"]
    assert window._job.fps == window._preset.fps


def _write_png(path: Path, width: int = 40, height: int = 30) -> Path:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(10, 20, 30))
    assert image.save(str(path), "PNG")
    return path


def test_inspector_uses_preset_fps_and_tokens(qapp: QApplication) -> None:
    del qapp
    window = MainWindow()
    window._preset.fps = 23.976
    window._preset.tokens["shot"] = "sh040"
    window._preset.tokens["note"] = "temp"
    window._refresh()
    assert window._inspector._shot_edit.text() == "sh040"
    assert window._inspector._note_edit.text() == "temp"
    assert window._inspector._read_fps() == 23.976
    tokens = window._tokens()
    assert tokens.shot == "sh040"
    assert tokens.note == "temp"
    assert tokens.fps == 23.976


def test_shot_note_and_fps_write_through_to_preset(
    qapp: QApplication, tmp_path: Path
) -> None:
    del qapp
    frames = [_write_png(tmp_path / f"clip.{i:04d}.png") for i in (1001, 1002)]
    window = MainWindow()
    window._load_paths(frames)
    window._on_shot("ep02_sh120")
    window._on_note("director cut")
    window._on_fps(30.0)
    assert window._preset.tokens["shot"] == "ep02_sh120"
    assert window._preset.tokens["note"] == "director cut"
    assert window._preset.fps == 30.0
    assert window._job is not None
    assert window._job.fps == 30.0
    assert window._tokens().fps == 30.0
    assert window._tokens().shot == "ep02_sh120"


def test_loading_preset_applies_fps_and_tokens(
    qapp: QApplication, tmp_path: Path
) -> None:
    del qapp
    frames = [_write_png(tmp_path / f"clip.{i:04d}.png") for i in (1001, 1002)]
    preset = default_preset()
    preset.fps = 25.0
    preset.tokens["shot"] = "loaded_shot"
    preset.tokens["note"] = "from json"
    path = tmp_path / "client.json"
    preset.save(path)
    window = MainWindow()
    window._load_paths(frames)
    window._load_preset(str(path))
    assert window._preset.fps == 25.0
    assert window._preset.tokens["shot"] == "loaded_shot"
    assert window._preset.tokens["note"] == "from json"
    assert window._job is not None
    assert window._job.fps == 25.0
    assert window._inspector._shot_edit.text() == "loaded_shot"
    assert window._inspector._note_edit.text() == "from json"
    assert window._inspector._read_fps() == 25.0


def test_open_uses_preset_fps(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    path = _write_png(tmp_path / "hero.png")
    window = MainWindow()
    window._preset.fps = 29.97
    window._load_paths([path])
    assert window._job is not None
    assert window._job.fps == 29.97


def test_save_preset_writes_fps_and_tokens(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    dest = tmp_path / "saved.json"
    window = MainWindow()
    window._preset_path = dest
    window._on_shot("saved_shot")
    window._on_note("saved note")
    window._on_fps(23.976)
    window._save_preset()
    loaded = Preset.load(dest)
    assert loaded.fps == 23.976
    assert loaded.tokens["shot"] == "saved_shot"
    assert loaded.tokens["note"] == "saved note"


def test_apply_launch_loads_dir_shot_and_preset(
    qapp: QApplication, tmp_path: Path
) -> None:
    del qapp
    frames = tmp_path / "frames"
    frames.mkdir()
    _write_png(frames / "clip.1001.png")
    _write_png(frames / "clip.1002.png")
    preset = default_preset()
    preset.fps = 25.0
    preset.tokens["shot"] = "from_json"
    preset_path = tmp_path / "show.json"
    preset.save(preset_path)
    window = MainWindow()
    window.apply_launch(
        LaunchArgs(path=str(frames), shot="maya_scene", preset=str(preset_path))
    )
    assert window._preset.fps == 25.0
    assert window._preset.tokens["shot"] == "maya_scene"
    assert window._inspector._shot_edit.text() == "maya_scene"
    assert window._job is not None
    assert window._job.kind == "sequence"
    assert window._job.count == 2
    assert window._job.fps == 25.0
    assert window._export_btn.isEnabled() is True


def test_apply_launch_selects_named_preset(qapp: QApplication) -> None:
    del qapp
    window = MainWindow()
    window.apply_launch(LaunchArgs(preset="prorigs"))
    assert window._preset.name == "prorigs"
    assert window._preset_path is not None
    assert window._preset_path.stem == "prorigs"
    selected = window._inspector._preset_name.currentData()
    assert Path(selected).resolve() == window._preset_path.resolve()
    assert window._inspector._preset_name.currentText() == "prorigs"


def test_apply_launch_single_image(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    still = _write_png(tmp_path / "hero.png")
    window = MainWindow()
    window.apply_launch(LaunchArgs(path=str(still), shot="still_shot"))
    assert window._job is not None
    assert window._job.kind == "still"
    assert window._preset.tokens["shot"] == "still_shot"


def test_export_complete_dialog(qapp: QApplication, tmp_path: Path, monkeypatch) -> None:
    del qapp
    still = _write_png(tmp_path / "hero.png")
    dest = tmp_path / "out.png"
    window = MainWindow()
    window._load_paths([still])
    messages: list[str] = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(dest), "PNG")
    )
    monkeypatch.setattr("glyph.main_window.export_still", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: messages.append(args[2] if len(args) > 2 else ""),
    )
    window._export()
    assert len(messages) == 1
    assert "Export complete" in messages[0]
    assert str(dest) in messages[0]


def test_safe_filename_from_shot_token() -> None:
    assert _safe_filename("ep01_sh010") == "ep01_sh010"
    assert _safe_filename('a:b/c?d') == "a_b_c_d"
