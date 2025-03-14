@echo off
SETLOCAL ENABLEEXTENSIONS

WHERE /Q uv
IF %ERRORLEVEL% NEQ 0 (
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)
CLS

TITLE Skycast
uv run --quiet --with prawcore^>=3.0.1 src/skycast.py

ENDLOCAL
PAUSE
