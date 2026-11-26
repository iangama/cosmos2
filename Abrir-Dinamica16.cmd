@echo off
cd /d "%~dp0"
".tooling\python\Scripts\python.exe" -Xutf8 "scripts\open-dynamics16-app.py"
if errorlevel 1 (
  echo Falha ao abrir o Cosmos2. Consulte o registro em output.
  pause
  exit /b 1
)
