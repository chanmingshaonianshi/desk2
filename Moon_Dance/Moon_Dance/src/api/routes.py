#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块
功能：定义所有API接口、请求校验、业务逻辑调度
作用：处理HTTP请求，参数校验，调用业务逻辑，返回响应
使用原因：与主入口分离，路由集中管理，便于接口维护和扩展
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Dict, Set, Tuple

from flask import Blueprint, jsonify, request

from src.api.auth import token_required
from src.config.settings import BASE_PATH, PROCESSED_IDS_FILE, UPLOAD_LOG_FILE, UPLOAD_REPORT_DIR, REDIS_URL
from src.utils.excel_exporter import export_daily_report
from src.utils.json_db import append_record, append_realtime_log, mark_request_processed
from src.core.worker import process_upload_data

api_bp = Blueprint("api", __name__)

_IDS_LOCK = threading.RLock()


def _json_error(message: str, status_code: int) -> Tuple[Any, int]:
    return jsonify({"ok": False, "message": message}), status_code


def _load_processed_ids() -> Set[str]:
    with _IDS_LOCK:
        if not os.path.exists(PROCESSED_IDS_FILE):
            return set()
        try:
            with open(PROCESSED_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {str(x) for x in data}
            return set()
        except Exception:
            return set()


def _save_processed_ids(processed_ids: Set[str]) -> None:
    os.makedirs(os.path.dirname(PROCESSED_IDS_FILE), exist_ok=True)
    payload = sorted(processed_ids)
    tmp_path = PROCESSED_IDS_FILE + ".tmp"
    with _IDS_LOCK:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, PROCESSED_IDS_FILE)


def _parse_device_id(device_id_value: Any) -> int:
    if device_id_value is None:
        return 0
    s = str(device_id_value).strip()
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    if s.startswith("device_"):
        tail = s.split("_", 1)[1]
        if tail.isdigit():
            return int(tail)
    return 0


def _process_upload(payload: Dict[str, Any]) -> Dict[str, Any]:
    dev_id = _parse_device_id(payload.get("device_id"))
    timestamp_ms = payload.get("timestamp")
    try:
        timestamp_ms_int = int(timestamp_ms)
    except Exception:
        timestamp_ms_int = int(time.time() * 1000)

    sensors = payload.get("sensors") or {}
    analysis = payload.get("analysis") or {}

    try:
        f_left = float(sensors.get("left_force_n", 0))
    except Exception:
        f_left = 0.0
    try:
        f_right = float(sensors.get("right_force_n", 0))
    except Exception:
        f_right = 0.0
    try:
        ratio = float(analysis.get("deviation_ratio", 0))
    except Exception:
        ratio = 0.0

    record: Dict[str, Any] = dict(payload)
    record.setdefault("timestamp", timestamp_ms_int)
    record["time"] = time.strftime("%H:%M:%S", time.localtime(timestamp_ms_int / 1000))
    record["ratio"] = ratio
    record["f_left"] = f_left
    record["f_right"] = f_right

    append_realtime_log(record, log_file_path=UPLOAD_LOG_FILE)

    if dev_id > 0:
        append_record(dev_id, record)

    os.makedirs(UPLOAD_REPORT_DIR, exist_ok=True)
    date_str = time.strftime("%Y%m%d")
    report_filename = f"upload_device_{dev_id:03d}_{date_str}.xls" if dev_id > 0 else f"upload_unknown_{date_str}.xls"
    time_point = record["time"]
    data_rows = [[str(dev_id), time_point, f"{f_left:.2f}", f"{f_right:.2f}", f"{ratio * 100:.2f}%"]]
    ok, report_path_or_err = export_daily_report(data_rows, filename=report_filename, output_dir=UPLOAD_REPORT_DIR)

    return {
        "device_id": dev_id,
        "timestamp": timestamp_ms_int,
        "report_ok": ok,
        "report_path": report_path_or_err if ok else None,
        "report_error": None if ok else report_path_or_err,
    }


@api_bp.post("/api/v1/upload")
@token_required
def upload_v1() -> Tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("request_id")
    if not request_id:
        return _json_error("缺少 request_id", 400)

    try:
        req_uuid = uuid.UUID(str(request_id))
    except Exception:
        return _json_error("request_id 必须是合法 UUID", 400)

    request_id_str = str(req_uuid)
    processed_ids = _load_processed_ids()
    if request_id_str in processed_ids:
        return jsonify({"ok": True, "message": "数据已处理", "request_id": request_id_str}), 200

    # 异步发送到Celery队列处理
    process_upload_data.delay(
        request_id=request_id_str,
        device_id=payload.get("device_id", ""),
        timestamp=payload.get("timestamp", int(time.time() * 1000)),
        sensors=payload.get("sensors", {}),
        analysis=payload.get("analysis", {})
    )
    
    # 先标记请求已处理，避免重复提交
    processed_ids.add(request_id_str)
    _save_processed_ids(processed_ids)

    return jsonify({"ok": True, "message": "数据已接收，正在异步处理", "request_id": request_id_str}), 202


@api_bp.post("/api/upload_data")
@token_required
def upload_legacy() -> Tuple[Any, int]:
    return upload_v1()

