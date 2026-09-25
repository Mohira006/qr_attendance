@echo off
REM Double-click this file to run setup.ps1 without needing to know about
REM PowerShell execution policies. %~dp0 is this .bat file's own folder,
REM so this works regardless of where it's run from - same reasoning as
REM $PSScriptRoot inside setup.ps1 itself.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
pause
