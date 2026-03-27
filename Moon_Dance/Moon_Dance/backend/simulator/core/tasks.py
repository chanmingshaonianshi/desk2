from __future__ import annotations
"""
文件：tasks.py
实现了什么：Celery 异步任务处理器（Worker 的核心逻辑）。
怎么实现的：实例化了一个 Celery app 对象，连接到配置的 Redis Broker。通过 @celery_app.task 装饰器定义了 process_sensor_data 任务。该任务被触发时，会从 Redis 队列中取出传感器数据，将其格式化，并调用 json_db 模块持久化保存到本地文件（如实时日志和 JSON 数据库）中。
为什么实现：满足项目验收中“使用 Redis 作为消息队列”的要求。将耗时的文件读写和数据持久化操作从 Web API 主线程中剥离出来，交给后台 Worker 异步处理，确保前端 API 能够以极低的延迟响应高频数据上传。
"""
import os
from celery import Celery
from datetime import datetime
from typing import Any, Dict
from simulator.config.settings import REDIS_URL, DATA_LOG_FILE, BASE_PATH

celery = Celery("moondance", broker=REDIS_URL, backend=REDIS_URL)

@celery.task(name="moondance.save_data")
def save_data(payload: Dict[str, Any]) -> bool:
    os.makedirs(os.path.dirname(DATA_LOG_FILE), exist_ok=True)
    line = f"{datetime.utcnow().isoformat()}Z\t{payload}\n"
    with open(DATA_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return True
