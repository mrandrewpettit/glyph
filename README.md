# Glyph

Windows app for burn-in bars on stills and image sequences.

## Setup

Python 3.11+, [uv](https://github.com/astral-sh/uv), and `ffmpeg` on `PATH` if you export video.

```bash
uv sync
uv run python -m glyph
```

Or double-click `Glyph.bat`.

## Use

| Input | Export |
| --- | --- |
| One image | PNG |
| Folder of images | MP4 |

## Tokens

Placeholders in bar text that Glyph fills in per frame — shot name, frame number, timecode, resolution, and so on.

`{filename}` `{shot}` `{note}` `{frame}` `{timecode}` `{date}` `{time}` `{datetime}` `{width}` `{height}` `{resolution}` `{fps}`

## Launch with a path

```bat
Glyph.bat "D:\playblasts\ep01_sh010" --shot ep01_sh010 --preset prorigs
Glyph.bat --input "D:\stills\hero.png" --shot ep01_sh010 --preset prorigs
```

- `--shot` / `-s` — shot name
- `--preset` / `-p` — preset name or path to a `.json` file
- Path — a still, or a folder of frames

## Tests

```bash
uv run pytest
```

## Still to do

- Remember last preset, Open folder, and Export folder
- Restore window size and position
- Store user presets in an app-data folder
- Font and color pickers
- Faster sequence export
- Color-managed EXR (OCIO)
- macOS and Linux

