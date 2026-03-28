#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON存储工具模块
功能：实时日志写入、幂等ID管理、JSON数据持久化
作用：轻量级数据存储，无需数据库即可满足数据落盘需求
使用原因：项目数据结构简单，JSON存储足够满足需求，部署维护简单
"""
import json
import os
import time
import threading
from src.config.settings import BASE_PATH, PROCESSED_IDS_FILE

DB_DIR = os.path.join(BASE_PATH, "data")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_FILE = os.path.join(DB_DIR, "history_data.json")
_DB_LOCK = threading.RLock()

REALTIME_LOG_DIR = os.path.join(DB_DIR, "realtime_logs")
if not os.path.exists(REALTIME_LOG_DIR):
    os.makedirs(REALTIME_LOG_DIR)
REALTIME_LOG_FILE = os.path.join(REALTIME_LOG_DIR, "realtime_log.jsonl")

def load_db():
    """Load history data from JSON file"""
    if not os.path.exists(DB_FILE):
        return {i: [] for i in range(1, 11)}  # Default for old UI compatibility
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # data structure: {"device_001": [records...], ...}
            # 为了兼容旧代码 (int keys)，我们需要转换一下
            # 但既然我们要面向未来，建议 UI 层也逐步改用字符串 ID
            # 这里先做一个混合处理
            result = {}
            for k, v in data.items():
                if k.startswith("device_"):
                    # New format: device_001 -> int(1) for old UI compatibility
                    try:
                        dev_id = int(k.split("_")[1])
                        result[dev_id] = v
                    except:
                        pass
                elif k.isdigit():
                    # Old format
                    result[int(k)] = v
            return result
    except Exception as e:
        print(f"Error loading DB: {e}")
        return {i: [] for i in range(1, 11)}

def save_db(data):
    """Save history data to JSON file"""
    try:
        export_data = {}
        for k, v in data.items():
            if isinstance(k, int):
                # Ensure device_id is 3 digits (e.g., device_001)
                export_data[f"device_{k:03d}"] = v
            else:
                export_data[k] = v
                
        with _DB_LOCK:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving DB: {e}")

def append_record(device_id, record):
    """
    Append a single record to the JSON file
    
    This function now handles the `realtime_data` format.
    Ideally, we should optimize this to avoid full file I/O on every write.
    For this simulation, it's acceptable.
    """
    with _DB_LOCK:
        data = load_db()
        if device_id in data:
            data[device_id].append(record)
        else:
            data[device_id] = [record]
        save_db(data)


def append_realtime_log(record, log_file_path=None):
    target_file = log_file_path or REALTIME_LOG_FILE
    target_dir = os.path.dirname(target_file)
    os.makedirs(target_dir, exist_ok=True)
    payload = dict(record)
    payload.setdefault("logged_at", int(time.time() * 1000))
    with _DB_LOCK:
        with open(target_file, 'a', encoding='utf-8', newline='') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def mark_request_processed(request_id):
    """
    标记请求ID为已处理，用于幂等校验
    :param request_id: 幂等请求ID
    """
    with _DB_LOCK:
        # 读取已处理ID列表
        if os.path.exists(PROCESSED_IDS_FILE):
            try:
                with open(PROCESSED_IDS_FILE, 'r', encoding='utf-8') as f:
                    processed_ids = set(json.load(f))
            except:
                processed_ids = set()
        else:
            processed_ids = set()
        
        # 添加新ID并保存
        processed_ids.add(request_id)
        # 最多保留最近10000个ID，避免文件过大
        if len(processed_ids) > 10000:
            processed_ids = set(list(processed_ids)[-10000:])
        
        os.makedirs(os.path.dirname(PROCESSED_IDS_FILE), exist_ok=True)
        with open(PROCESSED_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(processed_ids), f, ensure_ascii=False)
