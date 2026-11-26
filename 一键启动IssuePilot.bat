@echo off
chcp 65001 >nul
title IssuePilot
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-issuepilot.ps1"
if errorlevel 1 (
  echo.
  echo IssuePilot failed to start. Review the error above.
  pause
)

