from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenContext:
    filename: str = "hero_still.png"
    shot: str = "ep01_sh010"
    note: str = ""
    date: str = "2026-10-28"
    time: str = "14:32:08"
    frame: int = 1001
    start_frame: int = 1001
    index: int = 0
    fps: float = 24.0
    width: int = 1920
    height: int = 1080


TOKEN_CHIPS = (
    "{filename}",
    "{shot}",
    "{date}",
    "{time}",
    "{timecode}",
    "{frame}",
)


def timecode(index: int, fps: float, start_frame: int | None = None) -> str:
    del start_frame
    rate = fps if fps > 0 else 1.0
    elapsed = max(0, index) / rate
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = elapsed % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"


def resolve_line(template: str, ctx: TokenContext) -> str:
    return (
        template.replace("{filename}", ctx.filename)
        .replace("{shot}", ctx.shot)
        .replace("{note}", ctx.note)
        .replace("{date}", ctx.date)
        .replace("{time}", ctx.time)
        .replace("{datetime}", f"{ctx.date} {ctx.time}")
        .replace("{frame}", str(ctx.frame))
        .replace("{timecode}", timecode(ctx.index, ctx.fps))
        .replace("{width}", str(ctx.width))
        .replace("{height}", str(ctx.height))
        .replace("{resolution}", f"{ctx.width}x{ctx.height}")
        .replace("{fps}", str(ctx.fps))
    )
