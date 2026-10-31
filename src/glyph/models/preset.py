from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

SLOT_IDS = (
    "top-left",
    "top-middle",
    "top-right",
    "bottom-left",
    "bottom-middle",
    "bottom-right",
)

PLACE_ALIGNMENT = {
    "left": "left",
    "middle": "center",
    "right": "right",
}


class SlotKind(str, Enum):
    TEXT = "text"
    LOGO = "logo"


class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class Style:
    background: tuple[int, int, int, int] = (0, 0, 0, 160)
    font_color: tuple[int, int, int, int] = (255, 255, 255, 255)
    font_size_ratio: float = 0.45
    font_path: str | None = None


@dataclass
class Bar:
    height_ratio: float = 0.08


@dataclass
class Slot:
    kind: SlotKind
    alignment: Alignment
    margin: int = 8
    lines: list[str] = field(default_factory=list)
    image: str = ""

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind.value,
            "alignment": self.alignment.value,
            "margin": self.margin,
        }
        if self.kind is SlotKind.TEXT:
            data["lines"] = list(self.lines)
        else:
            data["image"] = self.image
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any], place: str) -> Slot:
        kind = SlotKind(data["kind"])
        alignment = Alignment(
            data.get("alignment", PLACE_ALIGNMENT.get(place, "left"))
        )
        return cls(
            kind=kind,
            alignment=alignment,
            margin=int(data.get("margin", 8)),
            lines=list(data.get("lines", [])),
            image=str(data.get("image", "")),
        )


@dataclass
class Preset:
    name: str
    style: Style
    top: Bar
    bottom: Bar
    slots: dict[str, Slot]
    fps: float = 24.0
    tokens: dict[str, str] = field(default_factory=lambda: {"shot": "ep01_sh010", "note": ""})

    def slot(self, slot_id: str) -> Slot:
        return self.slots[slot_id]

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "style": {
                "background": list(self.style.background),
                "font_color": list(self.style.font_color),
                "font_size_ratio": self.style.font_size_ratio,
                "font_path": self.style.font_path,
            },
            "fps": self.fps,
            "tokens": dict(self.tokens),
            "top": {"height_ratio": self.top.height_ratio},
            "bottom": {"height_ratio": self.bottom.height_ratio},
            "slots": {slot_id: slot.to_json() for slot_id, slot in self.slots.items()},
        }

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Preset:
        style_data = data.get("style", {})
        slots: dict[str, Slot] = {}
        raw_slots = data.get("slots", {})
        for slot_id in SLOT_IDS:
            place = slot_id.split("-", 1)[1]
            raw = raw_slots.get(slot_id) or {
                "kind": "text",
                "alignment": PLACE_ALIGNMENT[place],
                "margin": 8,
                "lines": [],
            }
            slots[slot_id] = Slot.from_json(raw, place)
        return cls(
            name=str(data.get("name", "untitled")),
            style=Style(
                background=_rgba(style_data.get("background"), (0, 0, 0, 160)),
                font_color=_rgba(style_data.get("font_color"), (255, 255, 255, 255)),
                font_size_ratio=float(style_data.get("font_size_ratio", 0.45)),
                font_path=style_data.get("font_path"),
            ),
            top=Bar(height_ratio=float(data.get("top", {}).get("height_ratio", 0.08))),
            bottom=Bar(
                height_ratio=float(data.get("bottom", {}).get("height_ratio", 0.08))
            ),
            slots=slots,
            fps=_fps(data.get("fps")),
            tokens=_tokens(data.get("tokens")),
        )

    @classmethod
    def load(cls, path: Path) -> Preset:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_json(data)


def presets_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "presets"


def bundled_default_path() -> Path:
    return presets_dir() / "default.json"


def resolve_preset_arg(value: str, folder: Path | None = None) -> Path:
    raw = Path(value).expanduser()
    candidates = [raw]
    if raw.suffix.lower() != ".json":
        candidates.append(raw.with_suffix(".json"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    key = value.strip().lower()
    if not key:
        raise FileNotFoundError("preset not found: empty name")
    items = list_presets(folder)
    for _label, path in items:
        if path.stem.lower() == key or path.name.lower() == key:
            return path
    for label, path in items:
        if label.lower() == key:
            return path
    raise FileNotFoundError(f"preset not found: {value}")


def list_presets(folder: Path | None = None) -> list[tuple[str, Path]]:
    root = folder if folder is not None else presets_dir()
    if not root.is_dir():
        return []
    items: list[tuple[str, Path]] = []
    seen: dict[str, int] = {}
    for path in sorted(root.glob("*.json"), key=lambda item: item.stem.lower()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            label = str(data.get("name") or path.stem)
        except (OSError, json.JSONDecodeError, TypeError):
            label = path.stem
        count = seen.get(label, 0)
        seen[label] = count + 1
        if count:
            label = f"{label} ({path.stem})"
        items.append((label, path.resolve()))
    return items


def default_preset() -> Preset:
    return Preset.from_json(
        {
            "name": "review",
            "style": {
                "background": [0, 0, 0, 160],
                "font_color": [255, 255, 255, 255],
                "font_size_ratio": 0.45,
                "font_path": None,
            },
            "fps": 24,
            "tokens": {"shot": "ep01_sh010", "note": ""},
            "top": {"height_ratio": 0.08},
            "bottom": {"height_ratio": 0.08},
            "slots": {
                "top-left": {
                    "kind": "text",
                    "alignment": "left",
                    "margin": 8,
                    "lines": ["{filename}"],
                },
                "top-middle": {
                    "kind": "text",
                    "alignment": "center",
                    "margin": 8,
                    "lines": [],
                },
                "top-right": {
                    "kind": "text",
                    "alignment": "right",
                    "margin": 8,
                    "lines": ["{date}", "{time}"],
                },
                "bottom-left": {
                    "kind": "text",
                    "alignment": "left",
                    "margin": 8,
                    "lines": ["{shot}"],
                },
                "bottom-middle": {
                    "kind": "logo",
                    "alignment": "center",
                    "margin": 8,
                    "image": "studio.png",
                },
                "bottom-right": {
                    "kind": "text",
                    "alignment": "right",
                    "margin": 8,
                    "lines": ["{timecode}", "{frame}"],
                },
            },
        }
    )


def _rgba(
    value: Any, fallback: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    if not value or len(value) != 4:
        return fallback
    return (int(value[0]), int(value[1]), int(value[2]), int(value[3]))


def _fps(value: Any) -> float:
    try:
        fps = float(value)
    except (TypeError, ValueError):
        return 24.0
    return fps if fps > 0 else 24.0


def _tokens(value: Any) -> dict[str, str]:
    tokens = {"shot": "ep01_sh010", "note": ""}
    if not isinstance(value, dict):
        return tokens
    for key, item in value.items():
        tokens[str(key)] = "" if item is None else str(item)
    return tokens
