from pathlib import Path

import pytest

from glyph.media.loader import infer_job, parse_frame, title_for, video_duration_text


def test_parse_frame_dot_padded(tmp_path: Path) -> None:
    path = tmp_path / "sh010_comp_v003.1001.exr"
    path.write_bytes(b"x")
    assert parse_frame(path) == 1001


def test_parse_frame_underscore() -> None:
    assert parse_frame(Path("plate_010.png")) == 10
    assert parse_frame(Path("hero_still.png")) is None
    assert parse_frame(Path("noext")) is None


def test_still_without_frame_starts_at_one(tmp_path: Path) -> None:
    path = tmp_path / "hero_still.png"
    path.write_bytes(b"x")
    job = infer_job([path])
    assert job.kind == "still"
    assert job.start_frame == 1
    assert job.count == 1
    assert title_for(job) == "hero_still.png"


def test_still_with_frame_keeps_number(tmp_path: Path) -> None:
    path = tmp_path / "beauty.0042.exr"
    path.write_bytes(b"x")
    job = infer_job([path])
    assert job.kind == "still"
    assert job.start_frame == 42


def test_sequence_natsort_and_title(tmp_path: Path) -> None:
    last = tmp_path / "shot.1010.png"
    first = tmp_path / "shot.1002.png"
    last.write_bytes(b"x")
    first.write_bytes(b"x")
    job = infer_job([last, first])
    assert job.kind == "sequence"
    assert job.start_frame == 1002
    assert job.files[0].name == "shot.1002.png"
    assert job.files[1].name == "shot.1010.png"
    assert title_for(job) == "shot.####.png  ·  2 files"


def test_natsort_orders_single_and_double_digits(tmp_path: Path) -> None:
    for name in ("clip.10.png", "clip.9.png", "clip.8.png"):
        (tmp_path / name).write_bytes(b"x")
    job = infer_job(list(tmp_path.glob("*.png")))
    assert [path.name for path in job.files] == [
        "clip.8.png",
        "clip.9.png",
        "clip.10.png",
    ]
    assert job.start_frame == 8


def test_ignores_non_images_and_missing(tmp_path: Path) -> None:
    good = tmp_path / "a.png"
    good.write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("nope")
    missing = tmp_path / "gone.jpg"
    job = infer_job([good, tmp_path / "notes.txt", missing])
    assert job.kind == "still"
    assert job.files == (good.resolve(),)


def test_uppercase_extension(tmp_path: Path) -> None:
    path = tmp_path / "STILL.PNG"
    path.write_bytes(b"x")
    job = infer_job([path])
    assert job.count == 1


def test_empty_selection_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no image files"):
        infer_job([tmp_path / "none.png"])


def test_sequence_without_frame_numbers(tmp_path: Path) -> None:
    a = tmp_path / "red.png"
    b = tmp_path / "blue.png"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    job = infer_job([b, a])
    assert job.kind == "sequence"
    assert job.start_frame == 1
    assert "2 files" in title_for(job)


def test_video_duration_scales_with_fps() -> None:
    assert video_duration_text(120, 24) == "Final Duration: 5.00"
    assert video_duration_text(120, 30) == "Final Duration: 4.00"
    assert video_duration_text(1500, 24) == "Final Duration: 62.50"


def test_fps_passthrough(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(b"x")
    job = infer_job([path], fps=23.976)
    assert job.fps == 23.976
