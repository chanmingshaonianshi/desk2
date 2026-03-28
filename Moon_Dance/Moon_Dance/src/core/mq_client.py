#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQ客户端模块
功能：Redis Stream消息队列客户端，实现消息发送、本地缓存、指数退避重传
作用：客户端发送数据到消息队列，保证数据不丢失，支持失败重传
使用原因：解耦客户端和服务端，提高系统可靠性和吞吐量
"""
import os
import json
import time
import uuid
import redis
from src.config.settings import REDIS_URL, TEMP_DIR

class MQClient:
    def __init__(self, device_id, redis_url=REDIS_URL, stream_name="upstream_data"):
        self.device_id = device_id
        self.stream_name = stream_name
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # 本地缓存目录
        self.cache_dir = os.path.join(TEMP_DIR, "client_cache", device_id)
        self.pending_dir = os.path.join(self.cache_dir, "pending")
        self.dead_letter_dir = os.path.join(self.cache_dir, "dead_letter")
        self.success_dir = os.path.join(self.cache_dir, "success")
        
        # 创建目录
        os.makedirs(self.pending_dir, exist_ok=True)
        os.makedirs(self.dead_letter_dir, exist_ok=True)
        os.makedirs(self.success_dir, exist_ok=True)
        
        # 重传配置
        self.max_retry = 10
        self.max_backoff = 30  # 最大重试间隔30秒
        self.pending_messages = {}  # 待重传的消息
        
        # 启动时加载本地待发送消息
        self._load_pending_messages()
    
    def _load_pending_messages(self):
        """加载本地缓存中待发送的消息"""
        for filename in os.listdir(self.pending_dir):
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(self.pending_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        msg = json.load(f)
                    self.pending_messages[msg["msg_id"]] = msg
                except Exception as e:
                    print(f"加载待发送消息失败 {filename}: {e}")
    
    def _save_pending_message(self, msg):
        """保存消息到本地待发送缓存"""
        filepath = os.path.join(self.pending_dir, f"{msg['msg_id']}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(msg, f, ensure_ascii=False, indent=2)
    
    def _move_to_dead_letter(self, msg):
        """消息超过重试次数，移入死信目录"""
        filepath = os.path.join(self.dead_letter_dir, f"{msg['msg_id']}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(msg, f, ensure_ascii=False, indent=2)
        # 从待发送目录删除
        pending_path = os.path.join(self.pending_dir, f"{msg['msg_id']}.json")
        if os.path.exists(pending_path):
            os.remove(pending_path)
        if msg["msg_id"] in self.pending_messages:
            del self.pending_messages[msg["msg_id"]]
    
    def _mark_send_success(self, msg_id):
        """标记消息发送成功"""
        # 从待发送列表移除
        if msg_id in self.pending_messages:
            msg = self.pending_messages.pop(msg_id)
            # 移动到成功目录（可选保留）
            filepath = os.path.join(self.success_dir, f"{msg_id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(msg, f, ensure_ascii=False, indent=2)
            # 删除待发送文件
            pending_path = os.path.join(self.pending_dir, f"{msg_id}.json")
            if os.path.exists(pending_path):
                os.remove(pending_path)
    
    def _get_retry_interval(self, retry_count):
        """指数退避计算重试间隔"""
        interval = min(2 ** retry_count, self.max_backoff)
        return interval
    
    def create_message(self, sensor_data, analysis_data=None):
        """创建标准化消息"""
        return {
            "msg_id": str(uuid.uuid4()),
            "device_id": self.device_id,
            "timestamp": int(time.time() * 1000),
            "data": {
                "sensors": sensor_data,
                "analysis": analysis_data or {}
            },
            "retry_count": 0,
            "create_time": int(time.time())
        }
    
    def send_message(self, msg):
        """发送消息到MQ，发送失败自动进入待重传队列"""
        try:
            # 发送到Redis Stream
            self.redis.xadd(
                self.stream_name,
                {"payload": json.dumps(msg, ensure_ascii=False)},
                id="*"
            )
            self._mark_send_success(msg["msg_id"])
            print(f"[MQ] 消息发送成功 {msg['msg_id']}")
            return True
        except Exception as e:
            print(f"[MQ] 消息发送失败 {msg['msg_id']}: {e}")
            msg["retry_count"] += 1
            msg["last_retry_time"] = int(time.time())
            
            if msg["retry_count"] >= self.max_retry:
                print(f"[MQ] 消息超过最大重试次数，移入死信 {msg['msg_id']}")
                self._move_to_dead_letter(msg)
            else:
                self.pending_messages[msg["msg_id"]] = msg
                self._save_pending_message(msg)
            return False
    
    def retry_pending_messages(self):
        """重试所有待发送的消息，由外部定时调用"""
        now = int(time.time())
        success_count = 0
        failed_count = 0
        
        for msg_id, msg in list(self.pending_messages.items()):
            retry_interval = self._get_retry_interval(msg["retry_count"])
            last_retry = msg.get("last_retry_time", 0)
            
            if now - last_retry >= retry_interval:
                print(f"[MQ] 重试发送消息 {msg_id} (第{msg['retry_count']}次)")
                if self.send_message(msg):
                    success_count += 1
                else:
                    failed_count += 1
        
        return success_count, failed_count
    
    def get_stats(self):
        """获取客户端统计信息"""
        return {
            "pending_count": len(self.pending_messages),
            "dead_letter_count": len(os.listdir(self.dead_letter_dir)),
            "success_count": len(os.listdir(self.success_dir))
        }
