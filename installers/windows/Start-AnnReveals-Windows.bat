@echo off
title Ann Reveals AI Manager v4.0 — Windows Desktop Application Launcher
setlocal EnableDelayedExpansion

echo ============================================================================
echo   ANN REVEALS AI MANAGER v4.0 (@annreveals)
echo   Single Application for Windows Laptop ^& Android Mobile
echo ============================================================================
echo.

cd /d "%~dp0..\.."
set "APP_ROOT=%CD%"
set "PORT=8080"
set "APP_URL=http://127.0.0.1:%PORT%"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [1/2] Starting local AnnRevealsApplication engine on %APP_URL% ...
    start "AnnRevealsBackend" /MIN python "%APP_ROOT%\backend\main.py"
    timeout /t 2 /nobreak >nul
    goto :LAUNCH_APP_WINDOW
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [1/2] Starting local AnnRevealsApplication engine on %APP_URL% ...
    start "AnnRevealsBackend" /MIN python3 "%APP_ROOT%\backend\main.py"
    timeout /t 2 /nobreak >nul
    goto :LAUNCH_APP_WINDOW
)

echo [INFO] Python not detected on PATH. Launching Standalone Portable Application directly...
set "APP_URL=file:///%APP_ROOT:\=/%/dist/AnnRevealsAIManager-Portable.html"

:LAUNCH_APP_WINDOW
echo [2/2] Opening Ann Reveals AI Manager native desktop window...
where msedge >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" msedge --app="%APP_URL%" --window-size=1360,880
    exit /b 0
)

where chrome >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" chrome --app="%APP_URL%" --window-size=1360,880
    exit /b 0
)

start "" "%APP_URL%"
exit /b 0
