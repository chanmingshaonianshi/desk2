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
import uuid
import requests
import json
import urllib3
from src.config.settings import API_KEY
from src.core.posture_analyzer import calculate_ratio, get_assessment, generate_force_data
from src.core.pressure_surface import generate_pressure_surface


class DeviceSimulator:
    """设备模拟器类"""
    def __init__(self, device_id, msg_queue, use_mq=True, api_url=None, api_token=None, verify_ssl=None, encrypt=False):
        self.device_id = device_id
        self.msg_queue = msg_queue
        self.history_data = []
        self.running = True
        self.use_mq = use_mq
        self.api_url = api_url if api_url is not None else os.environ.get("API_SERVER_URL", "").strip()
        self.api_token = api_token if api_token is not None else os.environ.get("API_BEARER_TOKEN", "").strip()
        self.api_key = os.environ.get("API_KEY", API_KEY).strip() or API_KEY
        if verify_ssl is None:
            verify_env = os.environ.get("API_VERIFY_SSL", "1").strip().lower()
            self.verify_ssl = verify_env not in {"0", "false", "no", "off"}
        else:
            self.verify_ssl = bool(verify_ssl)
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.encrypt = encrypt
        
        self.mq_client = None
        if self.use_mq:
            try:
                from src.core.mq_client import MQClient
                self.mq_client = MQClient(f"device_{device_id:03d}")
                self._start_retry_thread()
            except Exception as exc:
                self.use_mq = False
                print(f"[设备{self.device_id:02d}] MQ 已自动关闭: {exc}")
    
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
        
        surface = generate_pressure_surface(f_left, f_right)
        flat_surface = [val for row in surface for val in row]
        
        record = {
            "device_id": f"device_{self.device_id:03d}",
            "request_id": str(uuid.uuid4()),
            "timestamp": current_time,
            "sensors": {
                "left_force_n": round(f_left, 1),
                "right_force_n": round(f_right, 1),
                "total_force_n": round(f_left + f_right, 1)
            },
            "analysis": {
                "deviation_ratio": round(ratio, 4),
                "posture_status": color_tag,
                "health_score": int(100 - ratio * 100) if ratio < 1 else 0
            },
            "matrix_snapshot": {
                "resolution": [32, 32],
                "data": flat_surface
            }
        }
        
        record["time"] = time.strftime("%H:%M:%S")
        record["ratio"] = ratio
        record["f_left"] = f_left
        record["f_right"] = f_right
        
        self.history_data.append(record)
        
        log_msg = f"[{record['time']}] [设备编号 {self.device_id:02d}] 左侧: {f_left:.1f}N, 右侧: {f_right:.1f}N, 偏差率: {ratio*100:.1f}%, 状态: {status_text}"
        self.msg_queue.put((log_msg, color_tag, self.device_id, record))
        
        threading.Thread(target=self.send_to_api, args=(record,), daemon=True).start()
        
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
        if not self.api_url:
            return
        try:
            payload = {k: v for k, v in record.items() if k not in ["time", "ratio", "f_left", "f_right"]}
            
            if self.encrypt:
                from src.utils.crypto import encrypt_payload
                encrypted_str = encrypt_payload(payload)
                payload = {"encrypted_payload": encrypted_str}

            headers = {"X-API-Key": self.api_key}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=self.verify_ssl,
            )
            if response.status_code not in (200, 202):
                print(f"[API Error] Device {self.device_id}: Status {response.status_code}")
                return
            print(f"[API OK] Device {self.device_id}: Req {payload['request_id'][:8]} -> {response.status_code}")
        except Exception as e:
            print(f"[API Error] Device {self.device_id}: {e}")
    
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
