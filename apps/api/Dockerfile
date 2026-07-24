FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api /app
COPY src/MVP_web/utils /app/legacy/utils
COPY src/MVP_web/training /app/legacy/training
COPY src/MVP_web/coach /app/legacy/coach
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
