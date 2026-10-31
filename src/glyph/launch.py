from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchArgs:
    path: str | None = None
    shot: str | None = None
    preset: str | None = None


def parse_launch(argv: list[str]) -> tuple[LaunchArgs, list[str]]:
    parser = argparse.ArgumentParser(
        prog="glyph",
        description="Glyph — marks that stay on the frame.",
    )
    parser.add_argument(
        "--input",
        "-i",
        help="A still image, or a folder of frames (non-recursive).",
    )
    parser.add_argument(
        "--shot",
        "-s",
        help="Shot name for {shot} (overrides the preset token).",
    )
    parser.add_argument(
        "--preset",
        "-p",
        help="Preset name (e.g. prorigs) or path to a .json file.",
    )
    args, rest = parser.parse_known_args(argv[1:])
    positionals, qt_rest = _split_positionals(rest)
    path = args.input or (positionals[0] if positionals else None)
    program = argv[0] if argv else "glyph"
    return LaunchArgs(path=path, shot=args.shot, preset=args.preset), [
        program,
        *qt_rest,
    ]


def _split_positionals(rest: list[str]) -> tuple[list[str], list[str]]:
    positionals: list[str] = []
    qt_rest: list[str] = []
    index = 0
    while index < len(rest):
        item = rest[index]
        if item.startswith("-"):
            qt_rest.append(item)
            if index + 1 < len(rest) and not rest[index + 1].startswith("-"):
                qt_rest.append(rest[index + 1])
                index += 2
                continue
            index += 1
            continue
        positionals.append(item)
        index += 1
    return positionals, qt_rest
