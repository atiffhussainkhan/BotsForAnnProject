<#
.SYNOPSIS
    Installs Ann Reveals AI Manager v4.0 as a native Desktop & Start Menu application on Windows 10/11.
#>
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$LauncherBat = Join-Path $ScriptDir "Start-AnnReveals-Windows.bat"

Write-Host "Installing Ann Reveals AI Manager v4.0 on Windows..." -ForegroundColor Cyan

$WshShell = New-Object -ComObject WScript.Shell

# 1. Create Desktop Shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "Ann Reveals AI Manager.lnk"))
$DesktopShortcut.TargetPath = $LauncherBat
$DesktopShortcut.WorkingDirectory = $ProjectRoot
$DesktopShortcut.Description = "Ann Reveals AI Manager v4.0 — Instagram & TikTok Auto-Pilot"
$DesktopShortcut.Save()

# 2. Create Start Menu Shortcut
$StartMenuPath = [Environment]::GetFolderPath("Programs")
$StartShortcut = $WshShell.CreateShortcut((Join-Path $StartMenuPath "Ann Reveals AI Manager.lnk"))
$StartShortcut.TargetPath = $LauncherBat
$StartShortcut.WorkingDirectory = $ProjectRoot
$StartShortcut.Description = "Ann Reveals AI Manager v4.0 — Instagram & TikTok Auto-Pilot"
$StartShortcut.Save()

Write-Host "✅ Installed 'Ann Reveals AI Manager' on your Windows Desktop and Start Menu!" -ForegroundColor Green
Write-Host "Launching Ann Reveals AI Manager now..." -ForegroundColor Cyan
Start-Process -FilePath $LauncherBat
