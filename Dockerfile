FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn[standard]

# 复制代码
COPY backend/ backend/
COPY frontend/ frontend/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
