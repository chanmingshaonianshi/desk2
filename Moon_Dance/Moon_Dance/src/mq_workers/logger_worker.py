#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志统计工作节点
功能：记录系统运行指标、统计设备上报量、生成监控数据
作用：系统监控、流量统计、告警通知
使用原因：独立日志统计模块，不影响业务处理性能，单实例即可满足需求
"""
import os
import time
from collections import defaultdict
from .base_worker import BaseMQWorker
from src.config.settings import LOG_DIR

class LoggerWorker(BaseMQWorker):
    def __init__(self):
        super().__init__(
            worker_name="logger_worker",
            stream_name="validated_data",
            consumer_group="logger_group"
        )
        # 统计指标
        self.total_count = 0
        self.device_counts = defaultdict(int)
        self.last_report_time = int(time.time())
        self.report_interval = 60  # 每分钟输出一次统计报表
    
    def process_message(self, msg_id, payload):
        """统计消息指标"""
        try:
            device_id = payload["device_id"]
            self.total_count += 1
            self.device_counts[device_id] += 1
            
            # 定时输出统计报表
            now = int(time.time())
            if now - self.last_report_time >= self.report_interval:
                self._output_statistics()
                self.last_report_time = now
            
            return True
        except Exception as e:
            self._log(f"统计失败 {payload['msg_id']}: {e}", "ERROR")
            return False
    
    def _output_statistics(self):
        """输出统计报表"""
        total = self.total_count
        device_count = len(self.device_counts)
        top_devices = sorted(self.device_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        report = [
            "="*50,
            f"[流量统计报表] {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总处理消息数: {total}",
            f"在线设备数: {device_count}",
            "Top5上报设备:"
        ]
        
        for dev, cnt in top_devices:
            report.append(f"  {dev}: {cnt} 条")
        
        report.append("="*50)
        report_str = "\n".join(report)
        
        self._log("\n" + report_str)
        # 写入统计日志文件
        with open(os.path.join(LOG_DIR, "statistics.log"), 'a', encoding='utf-8') as f:
            f.write(report_str + "\n")

if __name__ == "__main__":
    worker = LoggerWorker()
    worker.run()
