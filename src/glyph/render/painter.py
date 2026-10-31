from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QPixmap

from glyph.layout.engine import Layout, Rect
from glyph.models.preset import Alignment, Preset, SlotKind
from glyph.models.tokens import TokenContext, resolve_line
from glyph.platform import default_font_path

_ALIGN = {
    Alignment.LEFT: Qt.AlignmentFlag.AlignLeft,
    Alignment.CENTER: Qt.AlignmentFlag.AlignHCenter,
    Alignment.RIGHT: Qt.AlignmentFlag.AlignRight,
}

_FONT_IDS: dict[str, str] = {}


def _qrect(rect: Rect) -> QRect:
    return QRect(rect.x, rect.y, rect.w, rect.h)


def _color(rgba: tuple[int, int, int, int]) -> QColor:
    return QColor(*rgba)


def _family_for(path: str | None) -> str:
    if not path:
        return "Arial"
    if path in _FONT_IDS:
        return _FONT_IDS[path]
    font_id = QFontDatabase.addApplicationFont(path)
    families = QFontDatabase.applicationFontFamilies(font_id)
    family = families[0] if families else "Arial"
    _FONT_IDS[path] = family
    return family


def draw_canvas(
    painter: QPainter,
    preset: Preset,
    layout: Layout,
    tokens: TokenContext,
    selected_id: str | None = None,
    plate: QPixmap | None = None,
) -> None:
    painter.fillRect(_qrect(layout.canvas), QColor(20, 20, 22))
    bar_color = _color(preset.style.background)
    painter.fillRect(_qrect(layout.top_bar), bar_color)
    painter.fillRect(_qrect(layout.bottom_bar), bar_color)

    plate_rect = _qrect(layout.plate)
    if plate is not None and not plate.isNull():
        painter.drawPixmap(plate_rect, plate)
    else:
        painter.fillRect(plate_rect, QColor(48, 50, 54))
        painter.setPen(QPen(QColor(70, 72, 78), 1))
        painter.drawLine(
            plate_rect.left(),
            plate_rect.top() + int(plate_rect.height() * 0.38),
            plate_rect.right(),
            plate_rect.top() + int(plate_rect.height() * 0.38),
        )
        painter.drawLine(
            plate_rect.left() + int(plate_rect.width() * 0.18),
            plate_rect.top(),
            plate_rect.left() + int(plate_rect.width() * 0.18),
            plate_rect.bottom(),
        )

    font_file = preset.style.font_path
    if not font_file:
        found = default_font_path()
        font_file = str(found) if found else None

    for slot_id, slot_layout in layout.slots.items():
        slot = preset.slot(slot_id)
        content = _qrect(slot_layout.content)
        if slot.kind is SlotKind.LOGO:
            _draw_logo(
                painter,
                slot.image,
                _qrect(slot_layout.slot),
                slot.margin,
                slot.alignment,
            )
        else:
            lines = [resolve_line(line, tokens) for line in slot.lines if line != ""]
            _draw_text(
                painter,
                lines,
                content,
                slot.alignment,
                slot_layout.bar.h,
                preset.style.font_size_ratio,
                _color(preset.style.font_color),
                font_file,
            )
        if slot_id == selected_id:
            painter.setPen(QPen(QColor(80, 160, 255), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(_qrect(slot_layout.slot).adjusted(0, 0, -1, -1))


def _draw_text(
    painter: QPainter,
    lines: list[str],
    rect: QRect,
    alignment: Alignment,
    bar_h: int,
    size_ratio: float,
    color: QColor,
    font_path: str | None,
) -> None:
    if not lines or rect.width() < 1 or rect.height() < 1:
        return
    font = QFont(_family_for(font_path))
    font.setPixelSize(max(8, int(bar_h * size_ratio)))
    painter.setFont(font)
    painter.setPen(color)
    metrics = QFontMetrics(font)
    line_h = metrics.height()
    total_h = line_h * len(lines)
    y = rect.y() + max(0, (rect.height() - total_h) // 2)
    align = int(_ALIGN[alignment] | Qt.AlignmentFlag.AlignVCenter)
    for line in lines:
        line_rect = QRect(rect.x(), y, rect.width(), line_h)
        painter.drawText(
            line_rect,
            align,
            metrics.elidedText(line, Qt.TextElideMode.ElideRight, rect.width()),
        )
        y += line_h


def padded_slot_rect(slot: QRect, margin: int) -> QRect:
    inset = max(0, margin)
    return QRect(
        slot.x() + inset,
        slot.y() + inset,
        max(0, slot.width() - inset * 2),
        max(0, slot.height() - inset * 2),
    )


def logo_dest_rect(
    src_w: int, src_h: int, dest: QRect, alignment: Alignment
) -> QRect:
    if dest.width() < 1 or dest.height() < 1:
        return QRect(dest.x(), dest.y(), 0, 0)
    src_w = max(1, src_w)
    src_h = max(1, src_h)
    scale = min(dest.width() / src_w, dest.height() / src_h)
    width = min(dest.width(), max(1, int(src_w * scale)))
    height = min(dest.height(), max(1, int(src_h * scale)))
    x = dest.x()
    if alignment is Alignment.CENTER:
        x = dest.x() + (dest.width() - width) // 2
    elif alignment is Alignment.RIGHT:
        x = dest.x() + dest.width() - width
    y = dest.y() + (dest.height() - height) // 2
    box = QRect(x, y, width, height)
    return box.intersected(dest)


def _draw_logo(
    painter: QPainter,
    image: str,
    slot: QRect,
    margin: int,
    alignment: Alignment,
) -> None:
    dest = padded_slot_rect(slot, margin)
    if dest.width() < 1 or dest.height() < 1:
        return
    path = Path(image) if image else None
    if path and path.is_file():
        pix = QPixmap(str(path))
        if not pix.isNull():
            box = logo_dest_rect(pix.width(), pix.height(), dest, alignment)
            if box.width() < 1 or box.height() < 1:
                return
            painter.save()
            painter.setClipRect(dest)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawPixmap(box, pix)
            painter.restore()
            return
    size = min(max(dest.height() - 4, 4), 64)
    box = logo_dest_rect(size, size, dest, alignment)
    painter.setPen(QPen(QColor(140, 140, 148), 1))
    painter.setBrush(QColor(40, 40, 44))
    painter.drawRect(box)
    painter.setPen(QColor(180, 180, 188))
    painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), "G")
