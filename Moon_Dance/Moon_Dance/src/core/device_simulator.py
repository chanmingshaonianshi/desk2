#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备模拟模块
功能：模拟多台智能坐垫设备生成压力数据、模拟真实采样间隔、MQ消息发送
作用：用于本地测试、功能演示、批量报表生成
使用原因：无需真实硬件即可测试整个系统链路，便于开发和演示
"""
"""
设备模拟器
"""
import random
import time
import threading
import os
import requests
import json
from src.core.posture_analyzer import calculate_ratio, get_assessment, generate_force_data
from src.core.pressure_surface import generate_pressure_surface
from src.core.mq_client import MQClient


class DeviceSimulator:
    """设备模拟器类"""
    def __init__(self, device_id, msg_queue, use_mq=True):
        self.device_id = device_id
        self.msg_queue = msg_queue
        self.history_data = []
        self.running = True
        self.use_mq = use_mq
        
        # 获取 API 服务器地址 (解耦设计)
        self.api_url = os.environ.get("API_SERVER_URL", "http://127.0.0.1:8000/api/upload_data")
        
        # 初始化MQ客户端
        if self.use_mq:
            self.mq_client = MQClient(f"device_{device_id:03d}")
            # 启动后台重传线程
            self._start_retry_thread()
    
    def _start_retry_thread(self):
        """启动后台重传线程，定时重试待发送消息"""
        def retry_worker():
            while self.running:
                try:
                    success, failed = self.mq_client.retry_pending_messages()
                    if success > 0 or failed > 0:
                        stats = self.mq_client.get_stats()
                        print(f"[设备{self.device_id:02d}] 重传结果：成功{success}条，失败{failed}条，待发送{stats['pending_count']}条")
                except Exception as e:
                    print(f"重传线程异常: {e}")
                time.sleep(1)
        
        thread = threading.Thread(target=retry_worker, daemon=True)
        thread.start()
        
    def measure(self):
        """执行一次测量"""
        f_left, f_right = generate_force_data()
        ratio = calculate_ratio(f_left, f_right)
        status_text, color_tag = get_assessment(ratio)
        current_time = int(time.time() * 1000)  # 毫秒级时间戳
        
        # 生成矩阵数据 (用于完整数据上传)
        surface = generate_pressure_surface(f_left, f_right)
        # 扁平化矩阵
        flat_surface = [val for row in surface for val in row]
        
        # 记录历史数据 (符合 realtime_data schema)
        record = {
            "device_id": f"device_{self.device_id:03d}",
            "timestamp": current_time,
            "sensors": {
                "left_force_n": round(f_left, 1),
                "right_force_n": round(f_right, 1),
                "total_force_n": round(f_left + f_right, 1)
            },
            "analysis": {
                "deviation_ratio": round(ratio, 4),
                "posture_status": color_tag,  # 使用 color_tag 作为状态标识
                "health_score": int(100 - ratio * 100) if ratio < 1 else 0
            },
            "matrix_snapshot": {
                "resolution": [32, 32],
                "data": flat_surface
            }
        }
        
        # 为了兼容旧代码的显示逻辑
        record["time"] = time.strftime("%H:%M:%S")
        record["ratio"] = ratio
        record["f_left"] = f_left
        record["f_right"] = f_right
        
        self.history_data.append(record)
        
        # 发送日志消息 (本地队列)
        log_msg = f"[{record['time']}] [设备编号 {self.device_id:02d}] 左侧: {f_left:.1f}N, 右侧: {f_right:.1f}N, 偏差率: {ratio*100:.1f}%, 状态: {status_text}"
        self.msg_queue.put((log_msg, color_tag, self.device_id, record))
        
        # 异步发送数据到 API (不阻塞主线程)
        threading.Thread(target=self.send_to_api, args=(record,), daemon=True).start()
        
        # 发送到MQ
        if self.use_mq:
            sensor_data = {
                "left_force_n": f_left,
                "right_force_n": f_right
            }
            analysis_data = {
                "deviation_ratio": ratio,
                "assessment": status_text
            }
            msg = self.mq_client.create_message(sensor_data, analysis_data)
            self.mq_client.send_message(msg)
        
        return record
    
    def send_to_api(self, record):
        """发送数据到 API 服务端"""
        try:
            # 清理掉用于 UI 兼容的非标准字段，只发送符合 Schema 的数据
            payload = {k: v for k, v in record.items() if k not in ["time", "ratio", "f_left", "f_right"]}
            
            response = requests.post(self.api_url, json=payload, timeout=2)
            if response.status_code != 200:
                print(f"[API Error] Device {self.device_id}: Status {response.status_code}")
        except Exception as e:
            # 网络错误不应崩溃，仅打印日志
            # print(f"[API Error] Device {self.device_id}: {e}")
            pass
    
    def get_history(self):
        """获取历史测量数据"""
        return self.history_data
    
    def clear_history(self):
        """清空历史数据"""
        self.history_data = []
        
    def stop(self):
        """停止模拟器"""
        self.running = False


def run_device_measurement(device_id, msg_queue):
    """运行设备测量任务，供多线程调用"""
    simulator = DeviceSimulator(device_id, msg_queue)
    simulator.measure()
    # history_store is no longer used, data is sent via msg_queue
