#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证工作节点
功能：验证原始上传数据的格式、完整性、业务规则合法性
作用：过滤非法数据，避免脏数据进入后续处理流程
使用原因：独立验证模块，可多副本运行提高处理速度，解耦验证逻辑和其他业务
"""
import uuid
from .base_worker import BaseMQWorker

class ValidatorWorker(BaseMQWorker):
    def __init__(self, worker_id=1):
        super().__init__(
            worker_name=f"validator_worker_{worker_id}",
            stream_name="upstream_data",
            consumer_group="validator_group"
        )
    
    def _validate_msg_format(self, payload):
        """验证消息格式是否符合规范"""
        # 必填字段检查
        required_fields = ["msg_id", "device_id", "timestamp", "data"]
        for field in required_fields:
            if field not in payload:
                return False, f"缺少必填字段 {field}"
        
        # msg_id必须是UUID
        try:
            uuid.UUID(payload["msg_id"])
        except:
            return False, "msg_id不是合法UUID"
        
        # 数据字段检查
        data = payload["data"]
        if "sensors" not in data:
            return False, "缺少sensors字段"
        
        sensors = data["sensors"]
        if "left_force_n" not in sensors or "right_force_n" not in sensors:
            return False, "压力数据不完整"
        
        # 数值范围检查
        try:
            left = float(sensors["left_force_n"])
            right = float(sensors["right_force_n"])
            if left < 0 or right < 0:
                return False, "压力值不能为负数"
        except:
            return False, "压力值不是合法数值"
        
        return True, "验证通过"
    
    def process_message(self, msg_id, payload):
        """验证消息并转发到下一个队列"""
        # 验证数据
        is_valid, reason = self._validate_msg_format(payload)
        if not is_valid:
            self._log(f"数据验证失败 {payload['msg_id']}: {reason}", "WARN")
            return False
        
        # 验证通过，转发到validated_data队列
        try:
            import json
            self.redis.xadd(
                "validated_data",
                {"payload": json.dumps(payload, ensure_ascii=False)},
                id="*"
            )
            self._log(f"数据验证通过 {payload['msg_id']}，已转发到validated_data队列")
            return True
        except Exception as e:
            self._log(f"转发到validated_data失败 {payload['msg_id']}: {e}", "ERROR")
            return False

if __name__ == "__main__":
    import sys
    worker_id = sys.argv[1] if len(sys.argv) > 1 else 1
    worker = ValidatorWorker(worker_id)
    worker.run()
