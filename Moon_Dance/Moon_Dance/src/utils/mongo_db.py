#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 数据存储模块
功能：异步向本地MongoDB数据库写入模拟器压力数据、提供数据查询接口
预留了服务器部署环境适配，可通过修改环境变量连接服务器的MongoDB。
"""

import os
import threading
import copy

try:
    from pymongo import MongoClient, DESCENDING
except ImportError:
    MongoClient = None
    DESCENDING = -1

# MongoDB 配置 (预留环境变量以便于服务器部署期间仅修改地址)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:123456@localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "pressure_simulator")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "pressure_data")

_mongo_client = None

def get_mongo_collection():
    global _mongo_client
    if MongoClient is None:
        return None
    
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            # 测试连接
            _mongo_client.admin.command('ping')
        except Exception as e:
            print(f"[MongoDB] 数据库连接失败: {e}")
            _mongo_client = None
            return None
    
    return _mongo_client[DB_NAME][COLLECTION_NAME]

def _insert_task(record):
    """后台插入数据的线程任务"""
    try:
        collection = get_mongo_collection()
        if collection is not None:
            collection.insert_one(record)
    except Exception as e:
        print(f"[MongoDB] 数据写入失败: {e}")

def insert_record_async(record):
    """
    异步将压力数据记录插入到MongoDB
    
    :param record: 字典格式的压力数据
    """
    if MongoClient is None:
        print("[MongoDB] 未安装 pymongo，跳过数据库写入")
        return
        
    # 深拷贝一份数据以防被其他线程修改，或者 _id 字段污染原字典
    record_copy = copy.deepcopy(record)
    thread = threading.Thread(target=_insert_task, args=(record_copy,))
    thread.daemon = True
    thread.start()

def get_latest_10_records():
    """
    查询最新 10 条压力数据
    
    :return: 包含最新 10 条压力数据的列表
    """
    try:
        collection = get_mongo_collection()
        if collection is None:
            return []
        
        # 默认使用内部创建时间 _id，或使用 logged_at 排序
        # 我们使用插入时的自然逆序获取最新的 10 条
        cursor = collection.find().sort([("_id", DESCENDING)]).limit(10)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] 查询最新 10 条数据失败: {e}")
        return []

def query_records_by_time(start_time_ms, end_time_ms):
    """
    按时间查询历史压力数据。依赖于数据中包含 logged_at (毫秒级时间戳)
    
    :param start_time_ms: 开始时间(毫秒级时间戳)
    :param end_time_ms: 结束时间(毫秒级时间戳)
    :return: 匹配的压力数据列表
    """
    try:
        collection = get_mongo_collection()
        if collection is None:
            return []
        
        query = {
            "logged_at": {
                "$gte": start_time_ms,
                "$lte": end_time_ms
            }
        }
        # 按照时间从早到晚排序
        cursor = collection.find(query).sort([("logged_at", 1)])
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] 按时间查询历史数据失败: {e}")
        return []
