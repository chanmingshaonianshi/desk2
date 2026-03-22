# 使用官方 Python 3.9 轻量版镜像
FROM python:3.9-slim

# 设置容器内的工作目录
WORKDIR /app

# 1. 复制依赖文件到容器
COPY requirements.txt .

# 2. 安装 Python 依赖
# 注意：tkinter 是 Python 标准库，通常不需要 pip 安装 'tk'。
# 这里使用 sed 命令在安装前移除 requirements.txt 中的 'tk'，避免 pip 报错。
# 同时更新 pip 源为国内镜像（可选，根据网络情况）
RUN sed -i '/^tk$/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 复制项目所有代码到容器工作目录
COPY . .

# 4. 创建数据存储目录（用于持久化挂载，可选）
RUN mkdir -p data

# API 默认使用 443 端口（HTTPS）
EXPOSE 443

# 5. 设置容器启动命令
# 使用 --no-gui 模式启动，并加上 --unbuffered 确保日志实时输出
CMD ["python3", "-u", "main.py", "--no-gui"]
