FROM python:3.12-slim
WORKDIR /app

# 安装共享层
COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

# 安装 Coach 后端依赖
COPY projects/coach/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 Coach 后端代码
COPY projects/coach/backend /app

# 复制知识库
COPY projects/coach/knowledge /app/projects/coach/knowledge

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
