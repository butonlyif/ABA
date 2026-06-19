@echo off
chcp 65001 >nul
title ABA智能助手 Windows 首次安装

cd /d %~dp0

echo.
echo ========================================
echo     ABA智能助手 Windows 首次安装
echo ========================================
echo.

py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=py -3.10
    goto found_python
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=py -3
    goto found_python
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PY_CMD=python
    goto found_python
)

echo 未检测到 Python。
echo 请先安装 Python 3.10 或 3.11，并勾选 Add Python to PATH。
echo 下载地址：https://www.python.org/downloads/windows/
pause
exit /b 1

:found_python
echo 检测到 Python：
%PY_CMD% --version

if not exist ".venv" (
    echo.
    echo 创建本地虚拟环境...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo 创建虚拟环境失败。
        pause
        exit /b 1
    )
)

echo.
echo 升级安装工具...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.
if exist "wheelhouse" (
    echo 从离线依赖目录安装...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links wheelhouse -r requirements-full.txt
) else (
    echo 未找到离线依赖目录，改为联网安装...
    ".venv\Scripts\python.exe" -m pip install -r requirements-full.txt
)

if errorlevel 1 (
    echo.
    echo 依赖安装失败。请确认 Python 版本为 3.10 或 3.11。
    pause
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo.
    echo 已创建 .env，请填入 API Key 后再启动。
)

if not exist "data\users" mkdir "data\users"
if not exist "data\chromadb" mkdir "data\chromadb"
if not exist "logs" mkdir "logs"

echo.
echo 安装完成。日常使用请双击 start_windows.bat
pause
