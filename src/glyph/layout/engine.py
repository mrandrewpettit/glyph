from __future__ import annotations

from dataclasses import dataclass

from glyph.models.preset import SLOT_IDS, Preset


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


@dataclass(frozen=True)
class SlotLayout:
    id: str
    bar: Rect
    slot: Rect
    content: Rect


@dataclass(frozen=True)
class Layout:
    source_width: int
    source_height: int
    canvas: Rect
    plate: Rect
    top_bar: Rect
    bottom_bar: Rect
    slots: dict[str, SlotLayout]


def bar_px(source_height: int, height_ratio: float) -> int:
    return max(0, round(source_height * height_ratio))


def compute_layout(preset: Preset, source_width: int, source_height: int) -> Layout:
    if source_width < 1 or source_height < 1:
        raise ValueError("source size must be at least 1x1")

    top_h = bar_px(source_height, preset.top.height_ratio)
    bottom_h = bar_px(source_height, preset.bottom.height_ratio)
    canvas = Rect(0, 0, source_width, source_height + top_h + bottom_h)
    top_bar = Rect(0, 0, source_width, top_h)
    plate = Rect(0, top_h, source_width, source_height)
    bottom_bar = Rect(0, top_h + source_height, source_width, bottom_h)

    slots: dict[str, SlotLayout] = {}
    for slot_id in SLOT_IDS:
        bar_id, _place = slot_id.split("-", 1)
        bar = top_bar if bar_id == "top" else bottom_bar
        slot_rect = _third(bar, _place_index(slot_id))
        margin = max(0, preset.slot(slot_id).margin)
        content_w = max(0, slot_rect.w - margin * 2)
        content = Rect(slot_rect.x + margin, slot_rect.y, content_w, slot_rect.h)
        slots[slot_id] = SlotLayout(
            id=slot_id, bar=bar, slot=slot_rect, content=content
        )

    return Layout(
        source_width=source_width,
        source_height=source_height,
        canvas=canvas,
        plate=plate,
        top_bar=top_bar,
        bottom_bar=bottom_bar,
        slots=slots,
    )


def _place_index(slot_id: str) -> int:
    place = slot_id.split("-", 1)[1]
    return {"left": 0, "middle": 1, "right": 2}[place]


def _third(bar: Rect, index: int) -> Rect:
    base = bar.w // 3
    leftover = bar.w - base * 3
    widths = [base, base, base + leftover]
    x = bar.x + sum(widths[:index])
    return Rect(x, bar.y, widths[index], bar.h)
