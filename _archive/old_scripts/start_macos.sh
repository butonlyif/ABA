#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "未检测到本地运行环境，先执行首次安装..."
    ./install_macos.sh
fi

if [ ! -f ".env" ]; then
    cp ".env.example" ".env"
    echo "已创建 .env，请填入 API Key 后重新运行。"
    exit 1
fi

mkdir -p data/users data/chromadb logs

echo ""
echo "ABA智能助手正在启动..."
echo "浏览器访问：http://localhost:8501"
echo "按 Ctrl+C 停止应用"
echo ""

".venv/bin/python" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
