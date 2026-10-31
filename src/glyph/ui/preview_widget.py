from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from glyph.layout.engine import Layout, compute_layout
from glyph.media.loader import IMAGE_EXTS
from glyph.models.preset import Preset
from glyph.models.tokens import TokenContext
from glyph.render.painter import draw_canvas


class PreviewWidget(QWidget):
    slotClicked = Signal(str)
    filesDropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self._preset: Preset | None = None
        self._tokens = TokenContext()
        self._selected_id = "bottom-right"
        self._plate: QPixmap | None = None
        self._has_media = False
        self._layout: Layout | None = None
        self._view = QRect()
        self.setMinimumSize(480, 360)
        self.setAutoFillBackground(True)
        self.setAcceptDrops(True)

    def set_state(
        self,
        preset: Preset,
        tokens: TokenContext,
        selected_id: str,
        plate: QPixmap | None = None,
        has_media: bool = False,
    ) -> None:
        self._preset = preset
        self._tokens = tokens
        self._selected_id = selected_id
        self._plate = plate
        self._has_media = has_media
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        if not self._has_media or self._preset is None:
            self._layout = None
            box = self.rect().adjusted(24, 24, -24, -24)
            painter.setPen(QPen(self.palette().mid().color(), 1, Qt.PenStyle.DashLine))
            painter.drawRect(box)
            painter.setPen(self.palette().windowText().color())
            painter.drawText(
                box,
                int(Qt.AlignmentFlag.AlignCenter),
                "Drop images here, or click Open",
            )
            return
        layout = compute_layout(
            self._preset, self._tokens.width, self._tokens.height
        )
        self._layout = layout
        scale = min(
            (self.width() - 32) / max(layout.canvas.w, 1),
            (self.height() - 32) / max(layout.canvas.h, 1),
        )
        draw_w = int(layout.canvas.w * scale)
        draw_h = int(layout.canvas.h * scale)
        x = (self.width() - draw_w) // 2
        y = (self.height() - draw_h) // 2
        self._view = QRect(x, y, draw_w, draw_h)
        painter.save()
        painter.translate(x, y)
        painter.scale(scale, scale)
        draw_canvas(
            painter,
            self._preset,
            layout,
            self._tokens,
            self._selected_id,
            self._plate,
        )
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._layout is None:
            return
        if not self._view.contains(event.position().toPoint()):
            return
        canvas_pt = self._to_canvas(event.position().toPoint())
        for slot_id, slot in self._layout.slots.items():
            rect = QRect(slot.slot.x, slot.slot.y, slot.slot.w, slot.slot.h)
            if rect.contains(canvas_pt):
                self.slotClicked.emit(slot_id)
                return

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _image_urls(event):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = _image_urls(event)
        if paths:
            event.acceptProposedAction()
            self.filesDropped.emit(paths)

    def _to_canvas(self, widget_pt: QPoint) -> QPoint:
        if self._layout is None or self._view.width() == 0:
            return widget_pt
        scale_x = self._layout.canvas.w / self._view.width()
        scale_y = self._layout.canvas.h / self._view.height()
        return QPoint(
            int((widget_pt.x() - self._view.x()) * scale_x),
            int((widget_pt.y() - self._view.y()) * scale_y),
        )


def _image_urls(event: QDragEnterEvent | QDropEvent) -> list[Path]:
    mime = event.mimeData()
    if not mime.hasUrls():
        return []
    paths: list[Path] = []
    for url in mime.urls():
        path = Path(url.toLocalFile())
        if path.suffix.lower() in IMAGE_EXTS:
            paths.append(path)
    return paths
