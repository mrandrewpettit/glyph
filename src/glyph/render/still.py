from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

from glyph.layout.engine import Layout
from glyph.models.preset import Preset
from glyph.models.tokens import TokenContext
from glyph.render.painter import draw_canvas


def render_image(
    preset: Preset,
    layout: Layout,
    tokens: TokenContext,
    plate: QPixmap | None,
) -> QImage:
    image = QImage(
        layout.canvas.w,
        layout.canvas.h,
        QImage.Format.Format_ARGB32,
    )
    image.fill(Qt.GlobalColor.black)
    painter = QPainter(image)
    try:
        draw_canvas(painter, preset, layout, tokens, selected_id=None, plate=plate)
    finally:
        painter.end()
    return image
