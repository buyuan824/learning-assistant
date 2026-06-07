FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python包
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（保持目录结构）
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# 设置工作目录为backend
WORKDIR /app/backend

# 复制.env.example到backend目录（可选）
COPY .env.example ./

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "app.py"]
