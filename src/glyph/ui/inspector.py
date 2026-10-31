from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from glyph.layout.engine import bar_px
from glyph.media.loader import video_duration_text
from glyph.models.preset import (
    SLOT_IDS,
    Alignment,
    Preset,
    Slot,
    SlotKind,
)
from glyph.models.tokens import TOKEN_CHIPS

_HEIGHT_RATIOS = ("0.06", "0.08", "0.1", "0.12")
_FONT_RATIOS = ("0.35", "0.45", "0.6")
_MARGINS = ("0", "4", "8", "16", "24")


def _place_label(slot_id: str) -> str:
    return slot_id.split("-", 1)[1].capitalize()


def _parse_int(text: str) -> int | None:
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    return int(digits)


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, spacing: int = 4) -> None:
        super().__init__(parent)
        self._items: list = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        space = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_height:
                x = rect.x()
                y += line_height + space
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + space
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class Inspector(QWidget):
    presetEdited = Signal()
    slotSelected = Signal(str)
    savePreset = Signal()
    savePresetAs = Signal()
    presetChosen = Signal(str)
    shotChanged = Signal(str)
    noteChanged = Signal(str)
    fpsChanged = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._preset: Preset | None = None
        self._selected_id = "bottom-right"
        self._shot = "ep01_sh010"
        self._note = ""
        self._source_h = 1080
        self._frame_count = 0
        self._syncing = False

        self.setMinimumWidth(280)
        self.setMaximumWidth(340)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(0)

        self._build_preset()
        self._build_sequence()
        self._build_tokens()
        self._build_style()
        self._top_list = self._build_slot_group("Top bar", "top")
        self._bottom_list = self._build_slot_group("Bottom bar", "bottom")

        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        self._editor = SlotEditor()
        self._editor.slotPatched.connect(self._on_patch)
        root.addWidget(self._editor, 0)

    def _section(self, title: str) -> QVBoxLayout:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 14)
        label = QLabel(title.upper())
        label.setStyleSheet("color: #9a9aa3; letter-spacing: 0.4px; font-size: 11px;")
        layout.addWidget(label)
        self._body.addWidget(frame)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3a3a40;")
        self._body.addWidget(line)
        return layout

    def _build_preset(self) -> None:
        layout = self._section("Preset")
        row = QHBoxLayout()
        self._preset_name = QComboBox()
        self._preset_name.setEditable(False)
        self._preset_name.activated.connect(self._on_preset_chosen)
        row.addWidget(self._preset_name, 1)
        menu_btn = QPushButton("···")
        menu_btn.setFixedWidth(32)
        menu = QMenu(menu_btn)
        menu.addAction("Save", self.savePreset.emit)
        menu.addAction("Save as…", self.savePresetAs.emit)
        menu_btn.setMenu(menu)
        menu_btn.setStyleSheet(
            "QPushButton::menu-indicator { image: none; width: 0; }"
        )
        row.addWidget(menu_btn)
        layout.addLayout(row)

    def _build_sequence(self) -> None:
        self._sequence_host = QWidget()
        host_layout = QVBoxLayout(self._sequence_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 14)
        label = QLabel("SEQUENCE")
        label.setStyleSheet("color: #9a9aa3; letter-spacing: 0.4px; font-size: 11px;")
        layout.addWidget(label)
        form = QFormLayout()
        self._fps = QComboBox()
        self._fps.setEditable(True)
        self._fps.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for text, value in (
            ("24 fps", 24.0),
            ("23.976 fps", 23.976),
            ("25 fps", 25.0),
            ("30 fps", 30.0),
        ):
            self._fps.addItem(text, value)
        self._fps.activated.connect(self._on_fps)
        self._fps.lineEdit().editingFinished.connect(self._on_fps)
        form.addRow("Frame rate", self._fps)
        layout.addLayout(form)
        self._duration = QLabel()
        self._duration.setWordWrap(True)
        self._duration.setStyleSheet("color: #9a9aa3; font-size: 11px;")
        layout.addWidget(self._duration)
        host_layout.addWidget(frame)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3a3a40;")
        host_layout.addWidget(line)
        self._body.addWidget(self._sequence_host)
        self._sequence_host.hide()

    def _on_fps(self) -> None:
        if self._syncing:
            return
        fps = self._read_fps()
        if fps is None:
            return
        self.fpsChanged.emit(fps)

    def _read_fps(self) -> float | None:
        data = self._fps.currentData()
        text = self._fps.currentText().strip()
        if data is not None and text == self._fps.itemText(self._fps.currentIndex()):
            return float(data)
        cleaned = text.lower().replace("fps", "").strip()
        try:
            value = float(cleaned)
        except ValueError:
            return None
        if value <= 0:
            return None
        return value

    def _fill_fps_combo(self, fps: float) -> None:
        self._fps.blockSignals(True)
        matched = False
        for index in range(self._fps.count()):
            data = self._fps.itemData(index)
            if data is not None and abs(float(data) - fps) < 1e-6:
                self._fps.setCurrentIndex(index)
                matched = True
                break
        if not matched:
            label = f"{int(fps)} fps" if float(fps).is_integer() else f"{fps:g} fps"
            existing = self._fps.findData(fps)
            if existing < 0:
                self._fps.addItem(label, fps)
                self._fps.setCurrentIndex(self._fps.count() - 1)
            else:
                self._fps.setCurrentIndex(existing)
        self._fps.blockSignals(False)

    def _build_tokens(self) -> None:
        layout = self._section("Tokens")
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self._shot_edit = QLineEdit()
        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText("optional")
        self._shot_edit.textChanged.connect(self._on_shot)
        self._note_edit.textChanged.connect(self._on_note)
        form.addRow("shot", self._shot_edit)
        form.addRow("note", self._note_edit)
        layout.addLayout(form)

    def _build_style(self) -> None:
        layout = self._section("Default style")
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self._bar_height = QComboBox()
        self._font_size = QComboBox()
        for combo in (self._bar_height, self._font_size):
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._bar_height.activated.connect(self._on_bar_height)
        self._bar_height.lineEdit().editingFinished.connect(self._on_bar_height)
        self._font_size.activated.connect(self._on_font_size)
        self._font_size.lineEdit().editingFinished.connect(self._on_font_size)
        form.addRow("Bar height", self._bar_height)
        form.addRow("Font size", self._font_size)
        layout.addLayout(form)

    def _height_label(self) -> str:
        ratio = 0.08
        if self._preset is not None:
            ratio = self._preset.top.height_ratio
        return f"Bar height  ·  {bar_px(self._source_h, ratio)} px"

    def _build_slot_group(self, title: str, bar: str) -> dict[str, QPushButton]:
        layout = self._section(title)
        buttons: dict[str, QPushButton] = {}
        for slot_id in SLOT_IDS:
            if not slot_id.startswith(bar):
                continue
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setStyleSheet("text-align: left; padding: 6px 8px;")
            btn.clicked.connect(lambda _=False, sid=slot_id: self.slotSelected.emit(sid))
            layout.addWidget(btn)
            buttons[slot_id] = btn
        return buttons

    def set_state(
        self,
        preset: Preset,
        selected_id: str,
        shot: str,
        note: str,
        source_height: int,
        sequence: bool = False,
        fps: float = 24.0,
        frame_count: int = 0,
    ) -> None:
        self._preset = preset
        self._selected_id = selected_id
        self._shot = shot
        self._note = note
        self._source_h = source_height
        self._syncing = True
        if self._shot_edit.text() != shot:
            self._shot_edit.setText(shot)
        if self._note_edit.text() != note:
            self._note_edit.setText(note)
        self._sequence_host.setVisible(sequence)
        self._frame_count = frame_count
        self._fill_fps_combo(fps)
        self._duration.setText(video_duration_text(frame_count, fps) if sequence else "")
        self._fill_height_combo()
        self._fill_font_combo()
        self._refresh_slot_lists()
        self._editor.set_slot(selected_id, preset.slot(selected_id))
        self._syncing = False

    def _fill_height_combo(self) -> None:
        self._bar_height.blockSignals(True)
        self._bar_height.clear()
        current = self._preset.top.height_ratio if self._preset else 0.08
        current_key = str(current)
        if current_key.endswith(".0"):
            current_key = current_key[:-2]
        matched = False
        for raw in _HEIGHT_RATIOS:
            px = bar_px(self._source_h, float(raw))
            self._bar_height.addItem(f"{px} px", float(raw))
            if abs(float(raw) - current) < 1e-9:
                self._bar_height.setCurrentIndex(self._bar_height.count() - 1)
                matched = True
        if not matched:
            self._bar_height.addItem(
                f"{bar_px(self._source_h, current)} px", current
            )
            self._bar_height.setCurrentIndex(self._bar_height.count() - 1)
        self._bar_height.blockSignals(False)

    def _fill_font_combo(self) -> None:
        self._font_size.blockSignals(True)
        self._font_size.clear()
        current = self._preset.style.font_size_ratio if self._preset else 0.45
        matched = False
        for raw in _FONT_RATIOS:
            self._font_size.addItem(f"{raw} of bar", float(raw))
            if abs(float(raw) - current) < 1e-9:
                self._font_size.setCurrentIndex(self._font_size.count() - 1)
                matched = True
        if not matched:
            bar_h = bar_px(self._source_h, self._preset.top.height_ratio) if self._preset else 1
            px = max(1, round(current * max(bar_h, 1)))
            self._font_size.addItem(f"{px} px", current)
            self._font_size.setCurrentIndex(self._font_size.count() - 1)
        self._font_size.blockSignals(False)

    def _refresh_slot_lists(self) -> None:
        assert self._preset is not None
        for slot_id, btn in {**self._top_list, **self._bottom_list}.items():
            slot = self._preset.slot(slot_id)
            if slot.kind is SlotKind.LOGO:
                preview = Path(slot.image).name if slot.image else "logo"
            else:
                preview = " / ".join(line for line in slot.lines if line) or "empty"
            btn.setText(f"{_place_label(slot_id)}    {preview}")
            btn.setChecked(slot_id == self._selected_id)

    def set_preset_list(self, items: list[tuple[str, Path]], current: Path | None) -> None:
        current_key = str(current.resolve()) if current is not None else ""
        self._preset_name.blockSignals(True)
        self._preset_name.clear()
        selected = -1
        for index, (label, path) in enumerate(items):
            self._preset_name.addItem(label, str(path))
            if str(path.resolve()) == current_key:
                selected = index
        if current is not None and selected < 0:
            self._preset_name.addItem(current.stem, str(current))
            selected = self._preset_name.count() - 1
        if selected >= 0:
            self._preset_name.setCurrentIndex(selected)
        self._preset_name.blockSignals(False)

    def _on_preset_chosen(self, index: int) -> None:
        if self._syncing:
            return
        path = self._preset_name.itemData(index)
        if path:
            self.presetChosen.emit(str(path))

    def _set_combo_data(self, combo: QComboBox, value: float) -> None:
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data is not None and abs(float(data) - value) < 1e-6:
                combo.setCurrentIndex(i)
                return

    def _on_shot(self, value: str) -> None:
        if not self._syncing:
            self.shotChanged.emit(value)

    def _on_note(self, value: str) -> None:
        if not self._syncing:
            self.noteChanged.emit(value)

    def _on_bar_height(self) -> None:
        if self._syncing or self._preset is None or self._source_h < 1:
            return
        data = self._bar_height.currentData()
        if data is not None and self._bar_height.currentText() == self._bar_height.itemText(
            self._bar_height.currentIndex()
        ):
            ratio = float(data)
        else:
            pixels = _parse_int(self._bar_height.currentText())
            if pixels is None:
                return
            ratio = pixels / self._source_h
        self._preset.top.height_ratio = ratio
        self._preset.bottom.height_ratio = ratio
        self.presetEdited.emit()

    def _on_font_size(self) -> None:
        if self._syncing or self._preset is None:
            return
        data = self._font_size.currentData()
        text = self._font_size.currentText().strip()
        if data is not None and text == self._font_size.itemText(
            self._font_size.currentIndex()
        ):
            ratio = float(data)
        else:
            try:
                value = float(text.split()[0])
            except (ValueError, IndexError):
                return
            if value >= 1:
                bar_h = bar_px(self._source_h, self._preset.top.height_ratio)
                if bar_h < 1:
                    return
                ratio = value / bar_h
            else:
                ratio = value
        self._preset.style.font_size_ratio = ratio
        self.presetEdited.emit()

    def _on_patch(self, patch: dict) -> None:
        if self._preset is None:
            return
        slot = self._preset.slot(self._selected_id)
        if "kind" in patch:
            slot.kind = SlotKind(patch["kind"])
        if "alignment" in patch:
            slot.alignment = Alignment(patch["alignment"])
        if "margin" in patch:
            slot.margin = int(patch["margin"])
        if "lines" in patch:
            slot.lines = list(patch["lines"])
        if "image" in patch:
            slot.image = str(patch["image"])
        self.presetEdited.emit()


class SlotEditor(QWidget):
    slotPatched = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._slot_id = "bottom-right"
        self._slot: Slot | None = None
        self._syncing = False
        self.setStyleSheet(
            "SlotEditor { background: #1c1c20; border-top: 1px solid #5090ff; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 14)

        header = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #5090ff;")
        self._title = QLabel("BOTTOM · RIGHT")
        self._title.setStyleSheet(
            "color: #5090ff; letter-spacing: 0.4px; font-weight: 600; font-size: 11px;"
        )
        header.addWidget(dot)
        header.addWidget(self._title)
        header.addStretch()
        layout.addLayout(header)

        form = QFormLayout()
        self._align = QComboBox()
        for value, label in (
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ):
            self._align.addItem(label, value)
        self._margin = QComboBox()
        for value in _MARGINS:
            self._margin.addItem(f"{value} px", int(value))
        self._kind = QComboBox()
        self._kind.addItem("Text", "text")
        self._kind.addItem("Logo", "logo")
        self._align.currentIndexChanged.connect(self._emit_align)
        self._margin.currentIndexChanged.connect(self._emit_margin)
        self._kind.currentIndexChanged.connect(self._emit_kind)
        form.addRow("Alignment", self._align)
        form.addRow("Margins", self._margin)
        form.addRow("Content", self._kind)
        layout.addLayout(form)

        self._text = QTextEdit()
        self._text.setAcceptRichText(False)
        self._text.setFixedHeight(84)
        self._text.textChanged.connect(self._emit_lines)
        self._text_label = QLabel("Text")
        layout.addWidget(self._text_label)
        layout.addWidget(self._text)

        self._chips = QWidget()
        self._chips.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        chips = FlowLayout(self._chips, spacing=4)
        for token in TOKEN_CHIPS:
            chip = QToolButton()
            chip.setText(f"+{token}")
            chip.setAutoRaise(True)
            chip.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 11px; padding: 4px 8px;"
            )
            chip.clicked.connect(lambda _=False, t=token: self._insert_token(t))
            chips.addWidget(chip)
        layout.addWidget(self._chips)

        self._logo_row = QWidget()
        logo_layout = QHBoxLayout(self._logo_row)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        self._logo_path = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self._logo_path.textChanged.connect(self._emit_image)
        logo_layout.addWidget(self._logo_path)
        logo_layout.addWidget(browse)
        self._logo_label = QLabel("Logo")
        layout.addWidget(self._logo_label)
        layout.addWidget(self._logo_row)

    def set_slot(self, slot_id: str, slot: Slot) -> None:
        self._slot_id = slot_id
        self._slot = slot
        self._syncing = True
        bar, place = slot_id.split("-", 1)
        self._title.setText(f"{bar.upper()} · {place.upper()}")
        self._set_combo(self._align, slot.alignment.value)
        self._set_combo(self._margin, slot.margin)
        self._set_combo(self._kind, slot.kind.value)
        joined = "\n".join(slot.lines)
        if self._text.toPlainText() != joined:
            self._text.setPlainText(joined)
        if self._logo_path.text() != slot.image:
            self._logo_path.setText(slot.image)
        is_text = slot.kind is SlotKind.TEXT
        self._text_label.setVisible(is_text)
        self._text.setVisible(is_text)
        self._chips.setVisible(is_text)
        self._logo_label.setVisible(not is_text)
        self._logo_row.setVisible(not is_text)
        self._syncing = False

    def _set_combo(self, combo: QComboBox, value: object) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _emit_align(self) -> None:
        if not self._syncing:
            self.slotPatched.emit({"alignment": self._align.currentData()})

    def _emit_margin(self) -> None:
        if not self._syncing:
            self.slotPatched.emit({"margin": self._margin.currentData()})

    def _emit_kind(self) -> None:
        if not self._syncing:
            self.slotPatched.emit({"kind": self._kind.currentData()})

    def _emit_lines(self) -> None:
        if not self._syncing:
            self.slotPatched.emit({"lines": self._text.toPlainText().split("\n")})

    def _emit_image(self, value: str) -> None:
        if not self._syncing:
            self.slotPatched.emit({"image": value})

    def _insert_token(self, token: str) -> None:
        cursor = self._text.textCursor()
        cursor.insertText(token)
        self._text.setTextCursor(cursor)
        self._text.setFocus()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Logo",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.webp);;All files (*.*)",
        )
        if path:
            self._logo_path.setText(path)
