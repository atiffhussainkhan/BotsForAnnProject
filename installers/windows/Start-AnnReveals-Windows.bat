@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0Install-AnnReveals-Windows.ps1" %*
if errorlevel 1 (
    echo Setup failed. Read the PowerShell message above.
    pause
    exit /b 1
)
