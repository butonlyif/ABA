#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "========================================"
echo "    ABA智能助手 macOS 首次安装"
echo "========================================"
echo ""

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "未检测到 Python 3。"
    echo "请先安装 Python 3.10 或 3.11：https://www.python.org/downloads/macos/"
    exit 1
fi

PY_VERSION="$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PY_VERSION" in
    3.10|3.11|3.12)
        echo "检测到 Python $PY_VERSION"
        ;;
    *)
        echo "当前 Python 版本为 $PY_VERSION，建议使用 Python 3.10、3.11 或 3.12。"
        ;;
esac

if [ ! -d ".venv" ]; then
    echo "创建本地虚拟环境..."
    "$PYTHON_CMD" -m venv .venv
fi

echo "升级安装工具..."
".venv/bin/python" -m pip install --upgrade pip

if [ -d "wheelhouse" ] && ls wheelhouse/*.whl >/dev/null 2>&1; then
    echo "从离线依赖目录安装..."
    ".venv/bin/python" -m pip install --no-index --find-links wheelhouse -r requirements-full.txt
else
    echo "未找到离线依赖目录，改为联网安装..."
    ".venv/bin/python" -m pip install -r requirements-full.txt
fi

if [ ! -f ".env" ]; then
    cp ".env.example" ".env"
    echo ""
    echo "已创建 .env。请填入 API Key 后再启动。"
fi

mkdir -p data/users data/chromadb logs

echo ""
echo "安装完成。日常使用请运行：./start_macos.sh"
