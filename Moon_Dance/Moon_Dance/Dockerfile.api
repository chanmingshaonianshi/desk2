# 官方 Python 3.11 轻量版镜像
FROM python:3.11-slim-bookworm

# 配置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# 设置容器内工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖，移除tk等GUI相关依赖
RUN sed -i '/^tk$/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir redis celery

# 复制项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p data/realtime_logs data/reports/uploads certs

# 暴露API端口
EXPOSE 8000

# 启动API服务
CMD ["python3", "-u", "main_api.py"]
