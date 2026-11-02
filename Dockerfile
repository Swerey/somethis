# SomeWhere 社区平台 - 后端镜像（批次四 Docker 化）
# 构建：docker build -t somewhere-backend -f Dockerfile .
# 运行依赖识别服务（recognizer）与可选 Redis，推荐用 docker-compose 一键编排
FROM python:3.11-slim

WORKDIR /app

# 先拷贝依赖清单并安装（利用层缓存，源码变更不触发重装）
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 拷贝后端源码与违规词词典
COPY backend /app/backend
COPY recognizer/badword_variants.json /app/recognizer/badword_variants.json

WORKDIR /app/backend

# 容器内路径化配置（本机绝对路径在镜像内不可用，全部改用环境变量注入）
ENV BADWORD_DICT=/app/recognizer/badword_variants.json \
    DATABASE_PATH=/app/data/hupu.db \
    PLATFORM_LOG_DIR=/app/logs \
    AUDIT_SERVICE_URL=http://recognizer:8000 \
    PLATFORM_REDIS_ENABLED=1 \
    PLATFORM_REDIS_URL=redis://redis:6379/0

EXPOSE 8080

# 与 main.py 一致：多 worker 启动（SQLite WAL 支持多进程）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
