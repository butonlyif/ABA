FROM python:3.12-slim
WORKDIR /app

# 安装共享层
COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

# 安装 ABA 后端依赖
COPY projects/aba/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 ABA 后端代码
COPY projects/aba/backend /app

# 复制知识库与闪卡素材
COPY projects/aba/knowledge /app/projects/aba/knowledge
COPY src/aba /app/assets:ro

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
