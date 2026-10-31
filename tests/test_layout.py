from __future__ import annotations

import pytest

from glyph.layout.engine import bar_px, compute_layout
from glyph.models.preset import SLOT_IDS, default_preset


def test_pad_on_bars_grow_canvas() -> None:
    preset = default_preset()
    preset.top.height_ratio = 100 / 2048
    preset.bottom.height_ratio = 100 / 2048
    layout = compute_layout(preset, 2048, 2048)
    assert layout.canvas.w == 2048
    assert layout.canvas.h == 2248
    assert layout.plate.w == 2048
    assert layout.plate.h == 2048
    assert layout.plate.y == 100
    assert layout.top_bar.h == 100
    assert layout.bottom_bar.y == 2148
    assert layout.bottom_bar.h == 100
    assert layout.plate.y == layout.top_bar.bottom
    assert layout.bottom_bar.y == layout.plate.bottom
    assert layout.plate.x == 0


def test_bar_height_shown_as_pixels() -> None:
    assert bar_px(1080, 0.08) == 86
    assert bar_px(2048, 0.08) == 164
    assert bar_px(100, 0) == 0
    assert bar_px(100, -1) == 0


def test_three_equal_slots_cover_bar_width() -> None:
    layout = compute_layout(default_preset(), 1920, 1080)
    top = [
        layout.slots["top-left"].slot,
        layout.slots["top-middle"].slot,
        layout.slots["top-right"].slot,
    ]
    assert top[0].x == 0
    assert top[0].w == top[1].w
    assert sum(slot.w for slot in top) == 1920
    assert top[2].right == 1920
    assert all(slot.y == 0 for slot in top)


def test_odd_width_remainder_goes_to_right_slot() -> None:
    layout = compute_layout(default_preset(), 100, 90)
    left = layout.slots["top-left"].slot
    mid = layout.slots["top-middle"].slot
    right = layout.slots["top-right"].slot
    assert left.w == 33
    assert mid.w == 33
    assert right.w == 34
    assert left.x == 0
    assert mid.x == 33
    assert right.x == 66
    assert right.right == 100


def test_margins_inset_left_and_right_only() -> None:
    preset = default_preset()
    preset.slot("top-left").margin = 16
    layout = compute_layout(preset, 1920, 1080)
    slot = layout.slots["top-left"]
    assert slot.content.x == slot.slot.x + 16
    assert slot.content.right == slot.slot.right - 16
    assert slot.content.y == slot.slot.y
    assert slot.content.h == slot.slot.h
    assert slot.content.h == layout.top_bar.h


def test_margin_cannot_invert_content() -> None:
    preset = default_preset()
    preset.slot("top-left").margin = 10_000
    layout = compute_layout(preset, 90, 90)
    assert layout.slots["top-left"].content.w == 0


def test_negative_margin_treated_as_zero() -> None:
    preset = default_preset()
    preset.slot("top-left").margin = -8
    layout = compute_layout(preset, 300, 100)
    slot = layout.slots["top-left"]
    assert slot.content.x == slot.slot.x
    assert slot.content.w == slot.slot.w


def test_independent_top_and_bottom_bar_heights() -> None:
    preset = default_preset()
    preset.top.height_ratio = 0.1
    preset.bottom.height_ratio = 0.2
    layout = compute_layout(preset, 100, 100)
    assert layout.top_bar.h == 10
    assert layout.bottom_bar.h == 20
    assert layout.canvas.h == 130
    assert layout.slots["top-left"].bar.h == 10
    assert layout.slots["bottom-left"].bar.h == 20


def test_zero_bar_keeps_plate_at_origin() -> None:
    preset = default_preset()
    preset.top.height_ratio = 0
    preset.bottom.height_ratio = 0
    layout = compute_layout(preset, 16, 9)
    assert layout.canvas.h == 9
    assert layout.plate.y == 0
    assert layout.bottom_bar.y == 9
    assert layout.bottom_bar.h == 0


def test_rejects_invalid_source_size() -> None:
    with pytest.raises(ValueError):
        compute_layout(default_preset(), 0, 1080)
    with pytest.raises(ValueError):
        compute_layout(default_preset(), 1920, 0)


def test_all_six_slots_present() -> None:
    layout = compute_layout(default_preset(), 1920, 1080)
    assert set(layout.slots) == set(SLOT_IDS)
