from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from glyph.launch import LaunchArgs
from glyph.media.loader import IMAGE_EXTS, MediaJob, collect_input, infer_job, title_for
from glyph.media.preview import load_plate
from glyph.models.preset import (
    Preset,
    bundled_default_path,
    default_preset,
    list_presets,
    presets_dir,
    resolve_preset_arg,
)
from glyph.models.tokens import TokenContext
from glyph.render.export import export_sequence, export_still
from glyph.render.ffmpeg import FFmpegError
from glyph.ui.inspector import Inspector
from glyph.ui.preview_widget import PreviewWidget

def _safe_filename(name: str) -> str:
    cleaned = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in name.strip())
    return cleaned.strip(" .")


_FILTER = (
    "Images ("
    + " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTS))
    + ");;All files (*.*)"
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Glyph")
        self.resize(1280, 780)
        self._preset_path = bundled_default_path()
        try:
            self._preset = Preset.load(self._preset_path)
        except OSError:
            self._preset = default_preset()
        self._selected_id = "bottom-right"
        self._job: MediaJob | None = None
        self._plate: QPixmap | None = None
        self._opened_at = datetime.now()

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._open)
        self._export_btn = QPushButton("Export")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        toolbar.addWidget(open_btn)
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(spacer)
        toolbar.addWidget(self._export_btn)

        self._title_files = QLabel("No files")
        self._title_files.setStyleSheet("color: #888; padding-left: 8px;")

        self._preview = PreviewWidget()
        self._inspector = Inspector()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._preview)
        splitter.addWidget(self._inspector)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 300])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(12, 6, 12, 6)
        name = QLabel("Glyph")
        name.setStyleSheet("font-weight: 600;")
        title_row.addWidget(name)
        title_row.addWidget(self._title_files)
        title_row.addStretch()
        layout.addLayout(title_row)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self._preview.slotClicked.connect(self._select_slot)
        self._preview.filesDropped.connect(self._load_paths)
        self._inspector.slotSelected.connect(self._select_slot)
        self._inspector.presetEdited.connect(self._refresh)
        self._inspector.shotChanged.connect(self._on_shot)
        self._inspector.noteChanged.connect(self._on_note)
        self._inspector.fpsChanged.connect(self._on_fps)
        self._inspector.savePreset.connect(self._save_preset)
        self._inspector.savePresetAs.connect(self._save_preset_as)
        self._inspector.presetChosen.connect(self._load_preset)
        self._refresh_preset_list()
        self._refresh()

    def apply_launch(self, launch: LaunchArgs) -> None:
        if launch.preset:
            try:
                preset_path = resolve_preset_arg(launch.preset)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Glyph", f"Could not load preset:\n{exc}")
            else:
                self._load_preset(str(preset_path))
        if launch.shot is not None:
            self._on_shot(launch.shot)
        if launch.path:
            try:
                files = collect_input(Path(launch.path))
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Glyph", str(exc))
                return
            self._load_paths(files)

    def _tokens(self) -> TokenContext:
        width, height = 1920, 1080
        filename = "hero_still.png"
        frame = 1001
        start = 1001
        fps = 24.0
        if self._job is not None and self._plate is not None:
            width = self._plate.width()
            height = self._plate.height()
            filename = self._job.first.name
            frame = self._job.start_frame
            start = self._job.start_frame
            fps = self._job.fps
        else:
            fps = self._preset.fps
        stamp = self._opened_at
        return TokenContext(
            filename=filename,
            shot=self._preset.tokens.get("shot", ""),
            note=self._preset.tokens.get("note", ""),
            date=stamp.strftime("%Y-%m-%d"),
            time=stamp.strftime("%H:%M:%S"),
            frame=frame,
            start_frame=start,
            fps=fps,
            width=width,
            height=height,
        )

    def _open(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Open", str(Path.home()), _FILTER)
        if paths:
            self._load_paths([Path(path) for path in paths])

    def _load_paths(self, paths: list[Path]) -> None:
        try:
            job = infer_job(paths, fps=self._preset.fps)
            plate = load_plate(job.first)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Glyph", str(exc))
            return
        if plate.isNull():
            QMessageBox.warning(self, "Glyph", "Could not read the first image.")
            return
        self._job = job
        self._plate = plate
        self._opened_at = datetime.now()
        self._refresh()

    def _select_slot(self, slot_id: str) -> None:
        self._selected_id = slot_id
        self._refresh()

    def _on_shot(self, value: str) -> None:
        self._preset.tokens["shot"] = value
        self._refresh()

    def _on_note(self, value: str) -> None:
        self._preset.tokens["note"] = value
        self._refresh()

    def _on_fps(self, fps: float) -> None:
        self._preset.fps = fps
        if self._job is not None:
            self._job = MediaJob(
                files=self._job.files,
                kind=self._job.kind,
                start_frame=self._job.start_frame,
                fps=fps,
            )
        self._refresh()

    def _refresh(self) -> None:
        tokens = self._tokens()
        has_media = self._job is not None
        self._export_btn.setEnabled(has_media)
        self._title_files.setText(
            title_for(self._job) if self._job is not None else "No files"
        )
        self._preview.set_state(
            self._preset,
            tokens,
            self._selected_id,
            self._plate,
            has_media,
        )
        self._inspector.set_state(
            self._preset,
            self._selected_id,
            self._preset.tokens.get("shot", ""),
            self._preset.tokens.get("note", ""),
            tokens.height,
            sequence=self._job is not None and self._job.kind == "sequence",
            fps=self._preset.fps,
            frame_count=self._job.count if self._job else 0,
        )

    def _export(self) -> None:
        if self._job is None or self._plate is None:
            return
        still = self._job.kind == "still"
        if still:
            name = f"{self._job.first.stem}.png"
        else:
            name = f"{_safe_filename(self._preset.tokens.get('shot', '')) or self._job.first.stem}.mp4"
        suggested = self._job.first.with_name(name)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export",
            str(suggested),
            "PNG (*.png)" if still else "MP4 (*.mp4)",
        )
        if not path:
            return
        dest = Path(path)
        if still and dest.suffix.lower() != ".png":
            dest = dest.with_suffix(".png")
        if not still and dest.suffix.lower() != ".mp4":
            dest = dest.with_suffix(".mp4")
        stamp = datetime.now()
        try:
            if still:
                tokens = self._tokens()
                tokens.date = stamp.strftime("%Y-%m-%d")
                tokens.time = stamp.strftime("%H:%M:%S")
                export_still(dest, self._preset, self._plate, tokens)
            else:
                progress = QProgressDialog(
                    "Exporting…", "Cancel", 0, self._job.count, self
                )
                progress.setWindowModality(Qt.WindowModality.ApplicationModal)
                progress.setMinimumDuration(0)
                cancelled = False

                def on_progress(done: int, total: int) -> None:
                    nonlocal cancelled
                    progress.setMaximum(total)
                    progress.setValue(done)
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        cancelled = True
                        raise RuntimeError("cancelled")

                try:
                    export_sequence(
                        dest,
                        self._preset,
                        self._job,
                        self._preset.tokens.get("shot", ""),
                        self._preset.tokens.get("note", ""),
                        stamp,
                        on_progress,
                    )
                finally:
                    progress.close()
                if cancelled:
                    return
        except FFmpegError as exc:
            QMessageBox.warning(self, "Glyph", f"FFmpeg failed:\n{exc}")
            return
        except OSError as exc:
            QMessageBox.warning(self, "Glyph", str(exc))
            return
        except RuntimeError:
            return
        QMessageBox.information(self, "Glyph", f"Export complete.\n\n{dest}")

    def _save_preset(self) -> None:
        self._preset.save(self._preset_path)
        self._refresh_preset_list()

    def _save_preset_as(self) -> None:
        presets_dir().mkdir(parents=True, exist_ok=True)
        suggested = presets_dir() / f"{self._preset.name or 'preset'}.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save preset",
            str(suggested),
            "Preset (*.json)",
        )
        if not path:
            return
        dest = Path(path)
        if dest.suffix.lower() != ".json":
            dest = dest.with_suffix(".json")
        self._preset_path = dest
        self._preset.name = dest.stem
        self._preset.save(dest)
        self._refresh_preset_list()
        self._refresh()

    def _load_preset(self, path_str: str) -> None:
        path = Path(path_str)
        try:
            self._preset = Preset.load(path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Glyph", f"Could not load preset:\n{exc}")
            self._refresh_preset_list()
            return
        self._preset_path = path.resolve()
        if self._job is not None:
            self._job = MediaJob(
                files=self._job.files,
                kind=self._job.kind,
                start_frame=self._job.start_frame,
                fps=self._preset.fps,
            )
        self._refresh_preset_list()
        self._refresh()

    def _refresh_preset_list(self) -> None:
        items = list_presets()
        if self._preset_path is not None:
            known = {path.resolve() for _label, path in items}
            if self._preset_path.resolve() not in known:
                items = [*items, (self._preset.name or self._preset_path.stem, self._preset_path)]
        self._inspector.set_preset_list(items, self._preset_path)
