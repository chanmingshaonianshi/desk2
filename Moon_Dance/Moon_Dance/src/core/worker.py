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
from celery import Celery
from src.config.settings import REDIS_URL, UPLOAD_LOG_FILE, PROCESSED_IDS_FILE
from src.utils.json_db import append_realtime_log, mark_request_processed

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
            "f_left": sensors["left_force_n"],
            "f_right": sensors["right_force_n"],
            "ratio": analysis["deviation_ratio"],
            "process_time": os.times()[4]
        }
        
        # 写入实时日志
        append_realtime_log(record)
        
        # 标记请求已处理（幂等）
        mark_request_processed(request_id)
        
        return {"status": "success", "request_id": request_id}
    except Exception as e:
        # 失败重试，最多3次
        self.retry(exc=e, countdown=2 ** self.request.retries)
