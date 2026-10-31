from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from glyph.layout.engine import compute_layout
from glyph.media.preview import load_plate
from glyph.models.preset import default_preset
from glyph.models.tokens import TokenContext
from PySide6.QtCore import QRect

from glyph.models.preset import Alignment
from glyph.render.painter import logo_dest_rect, padded_slot_rect
from glyph.render.still import render_image


def test_bars_pad_outside_plate_pixels(qapp: QApplication) -> None:
    del qapp
    plate = QPixmap(90, 60)
    plate.fill(QColor(255, 0, 0))
    preset = default_preset()
    preset.top.height_ratio = 0.1
    preset.bottom.height_ratio = 0.1
    preset.slot("top-middle").lines = []
    preset.slot("bottom-middle").kind = preset.slot("top-middle").kind
    preset.slot("bottom-middle").lines = []
    tokens = TokenContext(width=90, height=60, filename="red.png")
    layout = compute_layout(preset, 90, 60)
    image = render_image(preset, layout, tokens, plate)
    assert image.width() == 90
    assert image.height() == 72
    assert layout.plate.y == 6
    plate_pixel = image.pixelColor(10, layout.plate.y + 5)
    assert plate_pixel.red() == 255
    assert plate_pixel.green() == 0
    mid = layout.slots["top-middle"].content
    bar_pixel = image.pixelColor(mid.x + mid.w // 2, mid.y + max(mid.h // 2, 1))
    assert bar_pixel.red() < 40
    below = image.pixelColor(
        layout.slots["bottom-middle"].content.x
        + layout.slots["bottom-middle"].content.w // 2,
        layout.bottom_bar.y + max(layout.bottom_bar.h // 2, 1),
    )
    assert below.red() < 80


def test_logo_keeps_aspect_ratio() -> None:
    dest = QRect(0, 0, 300, 50)
    wide = logo_dest_rect(200, 40, dest, Alignment.CENTER)
    assert wide.height() == 50
    assert wide.width() == 250
    assert wide.x() == 25
    assert wide.bottom() <= dest.bottom()
    tall = logo_dest_rect(40, 200, dest, Alignment.LEFT)
    assert tall.height() == 50
    assert tall.width() == 10
    assert tall.x() == 0
    right = logo_dest_rect(100, 50, dest, Alignment.RIGHT)
    assert right.right() == dest.right()
    assert right.top() >= dest.top()
    assert right.bottom() <= dest.bottom()


def test_logo_scales_down_to_fit_padded_slot() -> None:
    slot = QRect(0, 0, 300, 80)
    dest = padded_slot_rect(slot, 8)
    assert dest == QRect(8, 8, 284, 64)
    fitted = logo_dest_rect(800, 200, dest, Alignment.CENTER)
    assert fitted.width() <= dest.width()
    assert fitted.height() <= dest.height()
    assert fitted.width() * 200 == fitted.height() * 800
    assert fitted.left() >= dest.left()
    assert fitted.right() <= dest.right()
    assert fitted.top() >= dest.top()
    assert fitted.bottom() <= dest.bottom()


def test_load_plate_roundtrip_png(qapp: QApplication, tmp_path: Path) -> None:
    del qapp
    source = QImage(32, 16, QImage.Format.Format_RGB32)
    source.fill(QColor(0, 255, 0))
    path = tmp_path / "green.png"
    assert source.save(str(path), "PNG")
    pix = load_plate(path)
    assert not pix.isNull()
    assert pix.width() == 32
    assert pix.height() == 16
    assert pix.toImage().pixelColor(1, 1).green() >= 250
