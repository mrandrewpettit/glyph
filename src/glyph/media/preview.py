from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def load_plate(path: Path) -> QPixmap:
    pix = QPixmap(str(path))
    if not pix.isNull():
        return pix
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        qimage = QImage(
            data,
            rgb.width,
            rgb.height,
            rgb.width * 3,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(qimage.copy())
