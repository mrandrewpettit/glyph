from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import tempfile

from PySide6.QtGui import QPixmap

from glyph.layout.engine import compute_layout
from glyph.media.loader import MediaJob, parse_frame
from glyph.media.preview import load_plate
from glyph.models.preset import Preset
from glyph.models.tokens import TokenContext
from glyph.render.ffmpeg import encode_png_sequence
from glyph.render.still import render_image


def export_still(
    dest: Path,
    preset: Preset,
    plate: QPixmap,
    tokens: TokenContext,
) -> None:
    layout = compute_layout(preset, tokens.width, tokens.height)
    image = render_image(preset, layout, tokens, plate)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(dest), "PNG"):
        raise OSError(f"could not write {dest}")


def export_sequence(
    dest: Path,
    preset: Preset,
    job: MediaJob,
    shot: str,
    note: str,
    stamp: datetime,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    first = load_plate(job.first)
    if first.isNull():
        raise OSError(f"could not read {job.first}")
    width, height = first.width(), first.height()
    with tempfile.TemporaryDirectory(prefix="glyph-") as raw:
        frames_dir = Path(raw)
        total = job.count
        for index, path in enumerate(job.files):
            plate = first if index == 0 else load_plate(path)
            if plate.isNull():
                raise OSError(f"could not read {path}")
            frame_n = parse_frame(path)
            if frame_n is None:
                frame_n = job.start_frame + index
            tokens = TokenContext(
                filename=path.name,
                shot=shot,
                note=note,
                date=stamp.strftime("%Y-%m-%d"),
                time=stamp.strftime("%H:%M:%S"),
                frame=frame_n,
                start_frame=job.start_frame,
                index=index,
                fps=job.fps,
                width=width,
                height=height,
            )
            layout = compute_layout(preset, width, height)
            image = render_image(preset, layout, tokens, plate)
            out = frames_dir / f"frame_{index + 1:04d}.png"
            if not image.save(str(out), "PNG"):
                raise OSError(f"could not write {out}")
            if progress:
                progress(index + 1, total)
        dest.parent.mkdir(parents=True, exist_ok=True)
        encode_png_sequence(frames_dir, dest, job.fps)
