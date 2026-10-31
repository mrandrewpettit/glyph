from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from glyph.launch import parse_launch
from glyph.main_window import MainWindow


def _dark_palette() -> QPalette:
    palette = QPalette()
    window = QColor(32, 32, 36)
    base = QColor(24, 24, 28)
    text = QColor(220, 220, 224)
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 44))
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, QColor(48, 48, 54))
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(80, 144, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, base)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    return palette


def run(argv: list[str] | None = None) -> int:
    raw = list(sys.argv if argv is None else argv)
    launch, qt_argv = parse_launch(raw)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(qt_argv)
    app.setApplicationName("Glyph")
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    icon_path = Path(__file__).resolve().parents[2] / "assets" / "glyph.svg"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.apply_launch(launch)
    window.show()
    return app.exec()
