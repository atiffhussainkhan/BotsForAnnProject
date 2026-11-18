@echo off
cd /d "%~dp0"
py -3 scripts\start_local.py verify
pause
