@echo off
setlocal
cd /d "%~dp0"
title Epic Seven - Repetir fase
if exist "%~dp0python\python.exe" (
    set "PYTHON_CMD=%~dp0python\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)
"%PYTHON_CMD%" "%~dp0tools\repeat_stage_launcher.py" %*
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
