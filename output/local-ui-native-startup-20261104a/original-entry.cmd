@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-cosmos2.ps1" -Built
if errorlevel 1 pause
