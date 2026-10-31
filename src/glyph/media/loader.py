from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from natsort import natsorted

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".webp", ".bmp"}
_FRAME = re.compile(r"^(.*?)([._])(\d+)\.(\w+)$", re.IGNORECASE)


@dataclass(frozen=True)
class MediaJob:
    files: tuple[Path, ...]
    kind: Literal["still", "sequence"]
    start_frame: int
    fps: float = 24.0

    @property
    def first(self) -> Path:
        return self.files[0]

    @property
    def count(self) -> int:
        return len(self.files)


def parse_frame(path: Path) -> int | None:
    match = _FRAME.match(path.name)
    if not match:
        return None
    return int(match.group(3))


def title_for(job: MediaJob) -> str:
    first = job.first
    if job.kind == "still":
        return first.name
    match = _FRAME.match(first.name)
    if match:
        hashes = "#" * len(match.group(3))
        pattern = f"{match.group(1)}{match.group(2)}{hashes}.{match.group(4)}"
    else:
        pattern = first.name
    return f"{pattern}  ·  {job.count} files"


def video_duration_text(frame_count: int, fps: float) -> str:
    if frame_count < 1 or fps <= 0:
        return ""
    return f"Final Duration: {frame_count / fps:.2f}"


def collect_input(path: Path) -> list[Path]:
    target = path.expanduser()
    if not target.exists():
        raise ValueError(f"not found: {path}")
    if target.is_file():
        return [target.resolve()]
    if not target.is_dir():
        raise ValueError(f"not a file or directory: {path}")
    files = [
        item.resolve()
        for item in target.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTS
    ]
    if not files:
        raise ValueError(f"no image files in {path}")
    return list(natsorted(files, key=lambda item: item.name))


def infer_job(paths: list[Path], fps: float = 24.0) -> MediaJob:
    files = [
        path.expanduser().resolve()
        for path in natsorted(paths, key=lambda item: item.name)
        if path.suffix.lower() in IMAGE_EXTS and path.is_file()
    ]
    if not files:
        raise ValueError("no image files")
    if len(files) == 1:
        start = parse_frame(files[0])
        return MediaJob(
            files=tuple(files),
            kind="still",
            start_frame=1 if start is None else start,
            fps=fps,
        )
    start = parse_frame(files[0])
    return MediaJob(
        files=tuple(files),
        kind="sequence",
        start_frame=1 if start is None else start,
        fps=fps,
    )
