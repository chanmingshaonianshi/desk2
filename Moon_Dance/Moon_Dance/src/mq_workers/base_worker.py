#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQ工作节点基类
功能：所有MQ工作模块的基类，实现通用的消费、ACK、异常处理逻辑
作用：统一工作节点的行为，减少重复代码，标准化错误处理
使用原因：所有工作节点都有类似的消费逻辑，基类实现后子类只需实现具体业务逻辑
"""
import os
import json
import time
import signal
import redis
from src.config.settings import REDIS_URL, LOG_DIR

class BaseMQWorker:
    def __init__(self, worker_name, stream_name, consumer_group, batch_size=10, block_time=1000):
        self.worker_name = worker_name
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.batch_size = batch_size
        self.block_time = block_time
        self.running = True
        
        # Redis连接
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        
        # 日志文件
        self.log_file = os.path.join(LOG_DIR, f"{worker_name}.log")
        
        # 初始化消费者组
        self._init_consumer_group()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _init_consumer_group(self):
        """初始化消费者组，如果不存在则创建"""
        try:
            self.redis.xgroup_create(self.stream_name, self.consumer_group, id="0", mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" not in str(e):
                raise
    
    def _handle_signal(self, signum, frame):
        """处理停止信号，优雅关闭"""
        print(f"\n收到停止信号，正在关闭 {self.worker_name}...")
        self.running = False
    
    def _log(self, message, level="INFO"):
        """写入日志"""
        log_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}\n"
        print(log_msg.strip())
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg)
    
    def _parse_message(self, message):
        """解析Redis Stream消息"""
        msg_id, fields = message
        try:
            payload = json.loads(fields["payload"])
            return msg_id, payload
        except Exception as e:
            self._log(f"消息解析失败 {msg_id}: {e}", "ERROR")
            # 解析失败的消息移入死信队列
            self._move_to_dead_letter(msg_id, fields)
            return msg_id, None
    
    def _move_to_dead_letter(self, msg_id, payload, reason=""):
        """将处理失败的消息移入死信队列"""
        try:
            self.redis.xadd(
                "dead_letter",
                {
                    "original_stream": self.stream_name,
                    "original_msg_id": msg_id,
                    "payload": payload.get("payload", json.dumps(payload)),
                    "reason": reason,
                    "worker_name": self.worker_name,
                    "error_time": int(time.time())
                },
                id="*"
            )
            # 确认消息已处理
            self.redis.xack(self.stream_name, self.consumer_group, msg_id)
        except Exception as e:
            self._log(f"移入死信队列失败 {msg_id}: {e}", "ERROR")
    
    def process_message(self, msg_id, payload):
        """
        子类实现具体的业务处理逻辑
        :param msg_id: Redis Stream消息ID
        :param payload: 解析后的消息内容
        :return: True处理成功，False处理失败
        """
        raise NotImplementedError("子类必须实现process_message方法")
    
    def run(self):
        """启动工作节点"""
        self._log(f"{self.worker_name} 启动成功，开始消费队列 {self.stream_name}")
        
        while self.running:
            try:
                # 读取消息
                messages = self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.worker_name,
                    streams={self.stream_name: ">"},
                    count=self.batch_size,
                    block=self.block_time
                )
                
                if not messages:
                    continue
                
                for stream_data in messages:
                    stream, msg_list = stream_data
                    for msg in msg_list:
                        msg_id, payload = self._parse_message(msg)
                        if not payload:
                            continue
                        
                        try:
                            success = self.process_message(msg_id, payload)
                            if success:
                                # 确认消息处理成功
                                self.redis.xack(self.stream_name, self.consumer_group, msg_id)
                                self._log(f"消息处理成功 {msg_id}")
                            else:
                                self._log(f"消息处理失败 {msg_id}", "ERROR")
                                self._move_to_dead_letter(msg_id, msg[1], reason="业务处理失败")
                        except Exception as e:
                            self._log(f"处理消息异常 {msg_id}: {e}", "ERROR")
                            self._move_to_dead_letter(msg_id, msg[1], reason=str(e))
                            
            except Exception as e:
                self._log(f"消费循环异常: {e}", "ERROR")
                time.sleep(1)
        
        self._log(f"{self.worker_name} 已停止")
