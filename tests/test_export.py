from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from glyph.layout.engine import compute_layout
from glyph.media.loader import infer_job
from glyph.models.preset import default_preset
from glyph.models.tokens import TokenContext
from glyph.render import export as export_mod
from glyph.render.export import export_sequence, export_still
from glyph.render.still import render_image


def test_still_export_png(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    plate = QPixmap(64, 48)
    plate.fill(QColor(40, 80, 120))
    preset = default_preset()
    tokens = TokenContext(width=64, height=48, filename="plate.png")
    dest = tmp_path / "out.png"
    export_still(dest, preset, plate, tokens)
    assert dest.is_file()
    image = QImage(str(dest))
    layout = compute_layout(preset, 64, 48)
    assert image.width() == layout.canvas.w
    assert image.height() == layout.canvas.h
    rendered = render_image(preset, layout, tokens, plate)
    assert rendered.width() == layout.canvas.w


def test_still_export_creates_parent_dirs(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    plate = QPixmap(16, 16)
    plate.fill(QColor(1, 2, 3))
    dest = tmp_path / "nested" / "burnin.png"
    export_still(
        dest,
        default_preset(),
        plate,
        TokenContext(width=16, height=16),
    )
    assert dest.is_file()


def test_sequence_export_writes_each_frame_then_encodes(
    qapp: QApplication, tmp_path: Path, monkeypatch
) -> None:
    del qapp
    frames: list[Path] = []
    for name in ("seq.1001.png", "seq.1002.png"):
        image = QImage(32, 24, QImage.Format.Format_RGB32)
        image.fill(QColor(90, 90, 90))
        path = tmp_path / name
        assert image.save(str(path), "PNG")
        frames.append(path)
    job = infer_job(frames, fps=24)
    seen: dict[str, object] = {}

    def fake_encode(frames_dir: Path, dest: Path, fps: float) -> None:
        pngs = sorted(frames_dir.glob("frame_*.png"))
        seen["count"] = len(pngs)
        seen["fps"] = fps
        seen["names"] = [p.name for p in pngs]
        dest.write_bytes(b"fake-mov")

    monkeypatch.setattr(export_mod, "encode_png_sequence", fake_encode)
    dest = tmp_path / "out.mp4"
    progress: list[tuple[int, int]] = []
    export_sequence(
        dest,
        default_preset(),
        job,
        shot="sh010",
        note="n",
        stamp=datetime(2026, 10, 28, 14, 32, 8),
        progress=lambda done, total: progress.append((done, total)),
    )
    assert dest.read_bytes() == b"fake-mov"
    assert seen["count"] == 2
    assert seen["fps"] == 24
    assert seen["names"] == ["frame_0001.png", "frame_0002.png"]
    assert progress == [(1, 2), (2, 2)]
