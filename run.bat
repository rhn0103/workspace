@echo off
REM 새 CMD 창에서 실행 (창이 바로 닫히지 않음)
set "LAUNCH_DIR=%~dp0."
start "AI Financial CRM" cmd /k "cd /d "%LAUNCH_DIR%" && run_main.bat"
