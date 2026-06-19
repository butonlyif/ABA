#!/bin/bash

# ====================================
# ABA智能助手 - 启动脚本
# ====================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    🌟 ABA智能助手 Web MVP 启动器    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python
echo -e "${YELLOW}检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ Python未安装！${NC}"
        echo "请先安装Python 3.9+"
        echo "下载地址：https://www.python.org/downloads/"
        exit 1
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# 检查pip
echo ""
echo -e "${YELLOW}检查pip...${NC}"
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}❌ pip未安装！${NC}"
    echo "请先安装pip"
    exit 1
fi
echo -e "${GREEN}✓ pip已安装${NC}"

# 检查.env文件
echo ""
echo -e "${YELLOW}检查配置文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env文件不存在，创建中...${NC}"
    cp ".env.example" ".env"
    echo -e "${GREEN}✓ 已创建.env文件${NC}"
    echo ""
    echo -e "${YELLOW}⚠️ 请编辑.env文件，填入你的API密钥！${NC}"
    echo ""
    echo "你可以使用以下命令打开编辑器："
    echo "  nano .env"
    echo "  或者"
    echo "  open -t .env"
    echo ""
    echo "MiniMax API密钥获取：https://platform.minimaxi.com"
    echo ""
    read -p "按Enter键继续..."
fi

# 创建必要的目录
echo ""
echo -e "${YELLOW}创建必要目录...${NC}"
mkdir -p data/users
mkdir -p data/chromadb
mkdir -p logs
mkdir -p knowledge_base_link
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 检查知识库目录
if [ -d "./知识库" ]; then
    echo ""
    echo -e "${YELLOW}检测到知识库目录：./知识库${NC}"
    echo -e "${GREEN}✓ 将使用该知识库${NC}"
elif [ -d "../知识库" ]; then
    echo ""
    echo -e "${YELLOW}检测到知识库目录：../知识库${NC}"
    echo -e "${GREEN}✓ 将使用该知识库${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️ 未找到知识库目录${NC}"
    echo "请确保知识库文件夹位于应用目录下，或与 MVP_web 目录平级。"
fi

# 安装依赖
echo ""
echo -e "${YELLOW}检查Python依赖...${NC}"
if [ -f "requirements.txt" ]; then
    $PYTHON_CMD -m pip install -r requirements.txt -q
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 依赖安装完成${NC}"
    else
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo "请手动运行：pip install -r requirements.txt"
        exit 1
    fi
else
    echo -e "${RED}⚠️ requirements.txt不存在${NC}"
fi

# 启动应用
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🚀 启动应用...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "应用启动后，浏览器将自动打开："
echo -e "${BLUE}http://localhost:8501${NC}"
echo ""
echo "按 Ctrl+C 停止应用"
echo ""

# 启动Streamlit
$PYTHON_CMD -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
