@echo off
chcp 65001 >nul 2>&1
setlocal enableextensions
title ABA Assistant

cd /d "%~dp0"

set "PY=%~dp0runtime\python.exe"
if not exist "%PY%" set "PY=%~dp0runtime\python\python.exe"

if not exist "%PY%" (
    echo [ERROR] Embedded Python not found:
    echo   %~dp0runtime\python.exe
    echo Please re-extract the zip and try again.
    pause
    exit /b 1
)

"%PY%" "%~dp0runtime\bootstrap.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo [Exit] code=%RC%
    pause
)

endlocal
exit /b %RC%
