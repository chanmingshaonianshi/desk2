#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celery异步任务处理模块
功能：处理API上传的坐姿数据，异步写入日志、生成报表
作用：解耦数据上传和计算逻辑，削峰填谷提高系统吞吐量
使用原因：高并发场景下避免API同步处理阻塞，提高系统可用性和响应速度
"""
import os
import json
import time
from celery import Celery
from src.config.settings import REDIS_URL, UPLOAD_LOG_FILE, PROCESSED_IDS_FILE
from src.utils.json_db import append_record, append_realtime_log, mark_request_processed

# 初始化Celery
celery = Celery(
    'moondance_worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
)

@celery.task(bind=True, max_retries=3)
def process_upload_data(self, request_id, device_id, timestamp, sensors, analysis):
    """
    异步处理上传的坐姿数据任务
    :param request_id: 幂等请求ID
    :param device_id: 设备ID
    :param timestamp: 数据时间戳
    :param sensors: 传感器数据（左右压力值）
    :param analysis: 预分析结果
    :return: 处理结果
    """
    try:
        # 构造数据记录
        record = {
            "request_id": request_id,
            "device_id": device_id,
            "timestamp": timestamp,
            "sensors": sensors or {},
            "analysis": analysis or {},
            "f_left": sensors.get("left_force_n", 0),
            "f_right": sensors.get("right_force_n", 0),
            "ratio": analysis.get("deviation_ratio", 0) if analysis else 0,
            "time": time.strftime("%H:%M:%S", time.localtime(int(timestamp) / 1000)),
            "process_time": os.times()[4]
        }
        
        # 写入实时日志与上传日志
        append_realtime_log(record)
        append_realtime_log(record, log_file_path=UPLOAD_LOG_FILE)

        try:
            device_text = str(device_id)
            if device_text.startswith("device_") and device_text.split("_", 1)[1].isdigit():
                append_record(int(device_text.split("_", 1)[1]), record)
        except Exception:
            pass
        
        # 标记请求已处理（幂等）
        mark_request_processed(request_id)
        
        return {"status": "success", "request_id": request_id}
    except Exception as e:
        # 失败重试，最多3次
        self.retry(exc=e, countdown=2 ** self.request.retries)
