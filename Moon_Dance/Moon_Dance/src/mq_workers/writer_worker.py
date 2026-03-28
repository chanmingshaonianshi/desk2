#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据写入工作节点
功能：将验证通过的数据写入文件系统、生成报表
作用：持久化存储业务数据，支持多副本水平扩展
使用原因：独立写入模块，可根据写入压力调整副本数，解耦存储逻辑
"""
import os
import json
import time
from .base_worker import BaseMQWorker
from src.config.settings import REALTIME_LOG_DIR
from src.utils.json_db import append_realtime_log

class WriterWorker(BaseMQWorker):
    def __init__(self, worker_id=1):
        super().__init__(
            worker_name=f"writer_worker_{worker_id}",
            stream_name="validated_data",
            consumer_group="writer_group"
        )
        # 设备日志文件按天分文件写入
        self.device_log_files = {}
    
    def _get_device_log_file(self, device_id):
        """获取设备对应的日志文件路径，按天拆分"""
        date_str = time.strftime("%Y%m%d")
        if device_id not in self.device_log_files or self.device_log_files[device_id]["date"] != date_str:
            filename = os.path.join(REALTIME_LOG_DIR, f"{device_id}_{date_str}.jsonl")
            self.device_log_files[device_id] = {
                "file": open(filename, 'a', encoding='utf-8'),
                "date": date_str
            }
        return self.device_log_files[device_id]["file"]
    
    def process_message(self, msg_id, payload):
        """写入数据到文件"""
        try:
            device_id = payload["device_id"]
            
            # 1. 写入统一的实时日志
            record = {
                "msg_id": payload["msg_id"],
                "device_id": device_id,
                "timestamp": payload["timestamp"],
                "data": payload["data"],
                "write_time": int(time.time())
            }
            append_realtime_log(record)
            
            # 2. 按设备单独写入日志文件
            log_file = self._get_device_log_file(device_id)
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            log_file.flush()
            
            self._log(f"数据写入成功 {payload['msg_id']} (设备: {device_id}")
            return True
        except Exception as e:
            self._log(f"数据写入失败 {payload['msg_id']}: {e}", "ERROR")
            return False
    
    def __del__(self):
        """关闭所有打开的文件句柄"""
        for dev_info in self.device_log_files.values():
            try:
                dev_info["file"].close()
            except:
                pass

if __name__ == "__main__":
    import sys
    worker_id = sys.argv[1] if len(sys.argv) > 1 else 1
    worker = WriterWorker(worker_id)
    worker.run()
