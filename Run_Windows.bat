@echo off
where /Q uv
if NOT %errorlevel% == 0 (
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)
cls
title Skycast
uv run --with prawcore^>=3.0.1 src/skycast.py
pause