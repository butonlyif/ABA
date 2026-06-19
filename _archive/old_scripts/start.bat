@echo off
chcp 65001 >nul
title ABA智能助手 Web MVP

echo.
echo ========================================
echo     🌟 ABA智能助手 Web MVP 启动器
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

REM 检查Python
echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装！
    echo 请先安装Python 3.9+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python已安装

REM 检查pip
echo.
echo 检查pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip未安装！
    pause
    exit /b 1
)
echo ✓ pip已安装

REM 检查.env文件
echo.
echo 检查配置文件...
if not exist ".env" (
    echo ⚠️ .env文件不存在，创建中...
    copy ".env.example" ".env" >nul
    echo ✓ 已创建.env文件
    echo.
    echo ⚠️ 请编辑.env文件，填入你的API密钥！
    echo.
    echo 豆包API密钥获取：https://console.volcengine.com/ark
    echo.
    pause
)

REM 创建目录
echo.
echo 创建必要目录...
if not exist "data\users" mkdir "data\users"
if not exist "data\chromadb" mkdir "data\chromadb"
if not exist "logs" mkdir "logs"
echo ✓ 目录创建完成

REM 检查知识库目录
echo.
if exist "知识库" (
    echo ✓ 检测到知识库目录：知识库
) else (
    if exist "..\知识库" (
        echo ✓ 检测到知识库目录：..\知识库
    ) else (
        echo ⚠️ 未找到知识库目录，请确保知识库文件夹位于应用目录下，或与 MVP_web 目录平级。
    )
)

REM 安装依赖
echo.
echo 检查Python依赖...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✓ 依赖安装完成
)

REM 启动应用
echo.
echo ========================================
echo 🚀 启动应用...
echo ========================================
echo.
echo 应用启动后，浏览器将自动打开：
echo http://localhost:8501
echo.
echo 按 Ctrl+C 停止应用
echo.

python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause
