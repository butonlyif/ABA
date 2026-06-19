@echo off
chcp 65001 >nul
title ABA智能助手

cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    echo 未检测到本地运行环境，先执行首次安装...
    call install_windows.bat
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo 已创建 .env，请填入 API Key 后重新运行。
    pause
    exit /b 1
)

if not exist "data\users" mkdir "data\users"
if not exist "data\chromadb" mkdir "data\chromadb"
if not exist "logs" mkdir "logs"

echo.
echo ABA智能助手正在启动...
echo 浏览器访问：http://localhost:8501
echo 按 Ctrl+C 停止应用
echo.

".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause
