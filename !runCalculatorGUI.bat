@echo off
REM Launch the Yantra calculator GUI (apps/calc/gui.py) — a button
REM calculator window whose arithmetic runs on the Sutra substrate.
REM Click the buttons or type; Enter = "=", Esc clears, Backspace deletes.
REM
REM First launch compiles the .su services and may download the embedding
REM model, so the window takes a few seconds to appear (a "compiling..."
REM line prints in this console meanwhile).
cd /d "%~dp0"
python apps\calc\gui.py
pause
