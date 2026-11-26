@echo off
cd /d "%~dp0"
"%~dp0.tooling\python\Scripts\python.exe" -Xutf8 "%~dp0scripts\open-working-cosmos2.py"
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0
