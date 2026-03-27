FROM python:3.9-slim

WORKDIR /app

# 安装必要的依赖
RUN pip install requests urllib3

# 复制客户端代码
COPY simulate_clients.py /app/simulate_clients.py

# 默认运行命令（可以通过 docker run 覆盖参数）
# 例如: docker run -d moondance-client python simulate_clients.py -n 5
ENTRYPOINT ["python", "simulate_clients.py"]
CMD ["-n", "3"]
