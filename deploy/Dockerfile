# ABA智能助手 - 生产部署镜像
# 基于轻量 python:3.11-slim
FROM python:3.11-slim

# 安装系统依赖（chromadb 需要 sqlite3 ≥ 3.35；slim 镜像默认带的就够新；保留 build-essential 是因为有些 wheel 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 docker layer cache：依赖不变时无需重装）
COPY src/MVP_web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制应用源码 + 构建索引所需的工具与知识库
# 注意：src/aba/图片(3.5GB) 与 图片卡_网络素材 不打进镜像，由 compose 挂载（见 .dockerignore）
COPY src/MVP_web/ /app/src/MVP_web/
COPY src/tools/ /app/src/tools/
COPY docs/知识库/ /app/docs/知识库/

# RAG 向量索引放在镜像内独立路径（不落在用户数据 volume 上），构建时一次性预建：
#  - 同时把本地 embedding 模型(MiniLM ~80MB)下载并烤进镜像层 → 运行时无需联网下载
ENV ABA_VECTOR_DB_PATH=/app/vectordb_index
RUN python /app/src/tools/ingest_kb.py

# 用户数据目录（档案 memory.db / 教练数据 / 缓存）将以 volume 挂载到这里
VOLUME ["/app/src/MVP_web/data"]

EXPOSE 8501 8503

# Streamlit 启动：
# - 监听 0.0.0.0，容器外可访问
# - 关闭 usage stats 上报（私有部署不想出网）
# - headless=true：不试图自动打开浏览器
WORKDIR /app/src/MVP_web
CMD ["streamlit", "run", "app_prototype.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]