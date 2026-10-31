@echo off
setlocal
cd /d "%~dp0"

set "PYW=%~dp0.venv\Scripts\pythonw.exe"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PYW%" if not exist "%PY%" (
    echo Glyph needs the project virtual environment.
    echo From this folder run:  uv sync
    echo Then double-click Glyph.bat again.
    pause
    exit /b 1
)

if exist "%PYW%" (
    start "" "%PYW%" -m glyph %*
) else (
    start "" "%PY%" -m glyph %*
)
exit /b 0
