#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动扩容监控脚本
根据Redis消息队列长度自动调整API服务副本数量
"""
import time
import subprocess
import redis
from typing import Optional

# 配置参数
SCALE_CONFIG = {
    "min_replicas": 3,          # 最小副本数
    "max_replicas": 10,         # 最大副本数
    "scale_up_threshold": 1000, # 队列长度超过该值扩容
    "scale_down_threshold": 100,# 队列长度低于该值缩容
    "scale_step": 1,            # 每次调整步长
    "cool_down_seconds": 60,    # 扩容/缩容冷却时间
    "check_interval_seconds": 10, # 检查间隔
    "redis_url": "redis://localhost:6379/0",
    "service_name": "api",
}

class AutoScaler:
    def __init__(self):
        self.redis_client = redis.from_url(SCALE_CONFIG["redis_url"])
        self.last_scale_time = 0
        self.current_replicas = SCALE_CONFIG["min_replicas"]

    def get_queue_length(self) -> int:
        """获取消息队列待处理任务数量"""
        try:
            # 检查Celery队列长度
            return self.redis_client.llen("celery")
        except Exception as e:
            print(f"获取队列长度失败: {e}")
            return 0

    def get_current_replicas(self) -> Optional[int]:
        """获取当前运行的副本数量"""
        try:
            cmd = [
                "docker", "compose", "ps", "--services", "--filter", "status=running"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            running_services = result.stdout.strip().split("\n")
            return running_services.count(SCALE_CONFIG["service_name"])
        except Exception as e:
            print(f"获取当前副本数失败: {e}")
            return None

    def scale_service(self, target_replicas: int) -> bool:
        """调整服务副本数量"""
        if target_replicas < SCALE_CONFIG["min_replicas"]:
            target_replicas = SCALE_CONFIG["min_replicas"]
        if target_replicas > SCALE_CONFIG["max_replicas"]:
            target_replicas = SCALE_CONFIG["max_replicas"]
        
        if target_replicas == self.current_replicas:
            return False

        try:
            print(f"调整服务副本数: {self.current_replicas} -> {target_replicas}")
            cmd = [
                "docker", "compose", "scale", f"{SCALE_CONFIG['service_name']}={target_replicas}"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            self.current_replicas = target_replicas
            self.last_scale_time = time.time()
            print(f"调整完成，当前副本数: {self.current_replicas}")
            return True
        except Exception as e:
            print(f"调整副本数失败: {e}")
            return False

    def run(self):
        """启动自动扩容监控"""
        print("启动自动扩容监控服务...")
        print(f"初始配置: 最小副本={SCALE_CONFIG['min_replicas']}, 最大副本={SCALE_CONFIG['max_replicas']}")
        
        while True:
            now = time.time()
            
            # 冷却时间检查
            if now - self.last_scale_time < SCALE_CONFIG["cool_down_seconds"]:
                time.sleep(SCALE_CONFIG["check_interval_seconds"])
                continue

            # 获取指标
            queue_len = self.get_queue_length()
            current_replicas = self.get_current_replicas()
            
            if current_replicas is None:
                time.sleep(SCALE_CONFIG["check_interval_seconds"])
                continue
            
            self.current_replicas = current_replicas
            
            print(f"当前状态: 队列长度={queue_len}, 副本数={current_replicas}")

            # 扩容判断
            if queue_len > SCALE_CONFIG["scale_up_threshold"]:
                if current_replicas < SCALE_CONFIG["max_replicas"]:
                    target = current_replicas + SCALE_CONFIG["scale_step"]
                    print(f"队列长度超过阈值，触发扩容: {current_replicas} -> {target}")
                    self.scale_service(target)
            
            # 缩容判断
            elif queue_len < SCALE_CONFIG["scale_down_threshold"]:
                if current_replicas > SCALE_CONFIG["min_replicas"]:
                    target = current_replicas - SCALE_CONFIG["scale_step"]
                    print(f"队列长度低于阈值，触发缩容: {current_replicas} -> {target}")
                    self.scale_service(target)

            time.sleep(SCALE_CONFIG["check_interval_seconds"])

if __name__ == "__main__":
    scaler = AutoScaler()
    scaler.run()
