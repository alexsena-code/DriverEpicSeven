@echo off
setlocal
cd /d "%~dp0"
title Epic Seven - Moonlight Theater
if exist "%~dp0python\python.exe" (
    set "PYTHON_CMD=%~dp0python\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)
"%PYTHON_CMD%" "%~dp0tools\theater_launcher.py" %*
set "RESULT=%ERRORLEVEL%"
if "%RESULT%"=="10" exit /b 0
pause
exit /b %RESULT%
